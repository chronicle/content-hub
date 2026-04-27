# ============================================================================#
# title           :VSphereManager.py
# description     :This Module contain all VSphere operations functionality
# author          :avital@siemplify.co
# date            :14-03-2018
# python_version  :2.7
# libreries       :pyvmomi
# requirments     :
# product_version :1.0
# ============================================================================#

# ============================= IMPORTS ===================================== #

from __future__ import annotations
from pyVmomi import vim, vmodl
from pyVim.connect import SmartConnect
from functools import reduce

# ============================== CONSTS ===================================== #


# ============================= CLASSES ===================================== #


class VSphereManagerError(Exception):
    """
    General Exception for VSphere manager
    """

    pass


class VSphereManager:

    def __init__(self, server_address, username, password, port=443):
        self.server_address = server_address
        self.username = username
        self.password = password
        self.port = port

        try:
            self.vcenter = SmartConnect(
                host=self.server_address,
                user=self.username,
                pwd=self.password,
                port=self.port,
            )

        except vim.fault.InvalidLogin:
            raise VSphereManagerError(
                "Cannot connect to specified host \
                using given username and password."
            )

        except Exception:
            try:
                # Try to connect via unsecured connection
                import ssl

                default_context = ssl._create_default_https_context
                ssl._create_default_https_context = ssl._create_unverified_context
                self.vcenter = SmartConnect(
                    host=self.server_address,
                    user=self.username,
                    pwd=self.password,
                    port=self.port,
                )
                ssl._create_default_https_context = default_context
            except Exception as exc1:
                raise VSphereManagerError(exc1)

    def get_obj_by_name(self, name, vimtypes=None, folder=None):
        """
        Get object by name, type and folder
        :param name: {str} The name of the object
        :param vimtypes: {[vim.*]} LIst of possible types to search among
        :param folder: {str} The folder to search in.
               If not given - will search in rootFolder
        :return: {vim.*} The found object
        """
        obj = None

        if not vimtypes:
            vimtypes = []

        if folder is not None:
            folder = self.get_obj_by_name(folder, [vim.Folder])
        else:
            folder = self.vcenter.content.rootFolder

        container = self.vcenter.content.viewManager.CreateContainerView(
            container=folder, type=vimtypes, recursive=True
        )

        for c in container.view:
            # Iterate over all found object and compare their names
            if name and c.name == name:
                obj = c
                break

        if obj:
            return obj

        raise VSphereManagerError(f"{name} not found.")

    def _get_obj(self, vimtypes, name):
        """
        Get object by name
        :param vimtypes: {list} Obj types to search among
        :param name: {str} The name of the object
        :return: {vim.*} The found object
        """
        if not vimtypes:
            vimtypes = []

        folder = self.vcenter.content.rootFolder
        obj = None
        container = self.vcenter.content.viewManager.CreateContainerView(
            container=folder, type=vimtypes, recursive=True
        )

        for c in container.view:
            # Iterate over all found object and compare their names
            if name and c.name == name:
                obj = c
                break

        if obj:
            return obj

        raise VSphereManagerError(f"{name} not found.")

    def _get_objects(self, vimtypes=None):
        """
        Get all objects of certain vimtypes
        :param vimtypes: {list} List of vimtypes
        :return: {list} List of found objects
        """
        if not vimtypes:
            vimtypes = []
        folder = self.vcenter.content.rootFolder
        container = self.vcenter.content.viewManager.CreateContainerView(
            container=folder, type=vimtypes, recursive=True
        )

        return container.view

    def get_all_vms(self):
        """
        Get all registered vms
        :return: [vim.VirutalMachine] List of virtual machines
        """
        return self._get_objects([vim.VirtualMachine])

    def get_vm_by_ip(self, ip):
        """
        Get vm by ip address
        :param ip: {str} The ip address
        :return: {vim.VirtualMachine} Vm with the given ip (if multiple
                 vms exists, returns the first)
        """
        search_index = self.vcenter.RetrieveContent().searchIndex
        vms = search_index.FindAllByIp(ip=ip, vmSearch=True)

        if vms:
            # Return the first vm with the given Ip
            return vms[0]

        raise VSphereManagerError(f"Vm with ip {ip} was not found.")

    def power_on_vm(self, vm):
        """
        Power on a vm
        :param vm: {vim.VirtualMachine} The vm to power on
        """
        task = vm.PowerOn()
        self.wait_for_task(task)

    def power_off_vm(self, vm):
        """
        Power off a vm
        :param vm: {vim.VirtualMachine} The vm to power off
        """
        task = vm.PowerOff()
        self.wait_for_task(task)

    def reset_vm(self, vm):
        """
        Hard reset a vm
        :param vm: {vim.VirtualMachine} The vm to reset
        """
        task = vm.ResetVM_Task()
        self.wait_for_task(task)

    def suspend_vm(self, vm):
        """
        Suspend a vm
        :param vm: {vim.VirtualMachine} The vm to suspend
        """
        task = vm.SuspendVM_Task()
        self.wait_for_task(task)

    def _build_task_filter(self, task):
        """
        From Pyvmomi-tools extension
        A helper that builds a filter for a particular task object.
        This method builds a property filter for use with a task object and
        :param task: {vim.Task} The task build the filter for
        :return: {vim.PropertyFilter} property filter for this object
        """

        pc = self.vcenter.content.propertyCollector

        obj_spec = [vmodl.query.PropertyCollector.ObjectSpec(obj=task)]
        prop_spec = vmodl.query.PropertyCollector.PropertySpec(
            type=vim.Task, pathSet=[], all=True
        )

        filter_spec = vmodl.query.PropertyCollector.FilterSpec()
        filter_spec.objectSet = obj_spec
        filter_spec.propSet = [prop_spec]
        filter = pc.CreateFilter(filter_spec, True)
        return filter

    def wait_for_task(self, task, *args, **kwargs):
        """
        From Pyvmomi-tools extension
        A helper method for blocking 'wait' based on the task class.
        This dynamic helper allows you to call .wait() on any task to keep the
        python process from advancing until the task is completed on the vCenter
        or ESX host on which the task is actually running.

        Only on observed task status transition will the callback fire. That is
        if the task is observed leaving queued and entering running, then the
        callback for 'running' is fired.
        :type task: vim.Task
        :param task: any subclass of the vim.Task object
        :rtype None: returns or raises exception
        :raises vim.RuntimeFault:
        """

        def no_op(task, *args):
            pass

        queued_callback = kwargs.get("queued", no_op)
        running_callback = kwargs.get("running", no_op)
        success_callback = kwargs.get("success", no_op)
        error_callback = kwargs.get("error", no_op)

        pc = self.vcenter.content.propertyCollector
        filter = self._build_task_filter(task)

        try:
            version, state = None, None

            # Loop looking for updates till the state moves to a completed state.
            waiting = True
            while waiting:
                update = pc.WaitForUpdates(version)
                version = update.version
                for filterSet in update.filterSet:
                    for objSet in filterSet.objectSet:
                        task = objSet.obj
                        for change in objSet.changeSet:
                            if change.name == "info":
                                state = change.val.state
                            elif change.name == "info.state":
                                state = change.val
                            else:
                                continue

                            if state == vim.TaskInfo.State.success:
                                success_callback(task, *args)
                                waiting = False

                            elif state == vim.TaskInfo.State.queued:
                                queued_callback(task, *args)

                            elif state == vim.TaskInfo.State.running:
                                running_callback(task, *args)

                            elif state == vim.TaskInfo.State.error:
                                error_callback(task, *args)
                                raise task.info.error

        finally:
            if filter:
                filter.Destroy()

    def get_snapshot_by_name(self, vm, snapname):
        """
        Get snapshot object by name
        :param vm: {vim.VirtualMachine} The vm object that owns the snapshot
        :param snapname: {str} The snapshot name
        :return: {vim.Snapshot} The found snapshot
        """
        return self._get_snapshot_by_name_recursively(
            vm.snapshot.rootSnapshotList, snapname
        )

    def _get_snapshot_by_name_recursively(self, snapshots, snapname):
        """
        Get snapshot object by name recursively
        :param snapshots: {vim.SnapshotTree} The snapshot root tree
        :param snapname: {str} The snapshot name
        :return: {vim.Snapshot} The found snapshot
        """
        for snapshot in snapshots:
            if snapshot.name == snapname:
                return snapshot.snapshot
            else:
                return self._get_snapshot_by_name_recursively(
                    snapshot.childSnapshotList, snapname
                )

    def _get_current_snap_obj(self, snapshots, snapobj):
        """
        Get current snapshot object recursively
        :param snapshots: {vim.SnapshotTree} The snapshot root tree
        :param snapobj: {vim.Snapshot} The desired snapshot object
        :return: {vim.Snapshot} The found snapshot
        """
        for snapshot in snapshots:
            if snapshot.snapshot == snapobj:
                return snapshot.snapshot
            else:
                return self._get_current_snap_obj(snapshot.childSnapshotList, snapobj)

    def get_current_snapshot(self, vm):
        """
        Get current snapshot object
        :param vm: {vim.VirtualMachine} The vm
        :return: {vim.Snapshot} The current snapshot
        """
        return self._get_current_snap_obj(
            vm.snapshot.rootSnapshotList, vm.snapshot.currentSnapshot
        )

    def _revert_to_snapshot(self, snapobj):
        """
        Revert to snapshot
        :param snapobj: {vim.Snapshot} The snapshot to revert to
        """
        task = snapobj.RevertToSnapshot_Task()
        self.wait_for_task(task)

    def revert_to_snapshot(self, vm, snapshot_name=None):
        """
        Revert to snapshot
        :param vm: {vim.VirtualMachine} The vm to revert
        :param snapshot_name: {str} The name of the snapshot to revert to.
               Optional - if not given, will be reverted to current snapshot
        """
        if not snapshot_name:
            snapobj = self.get_current_snapshot(vm)
        else:
            snapobj = self.get_snapshot_by_name(vm, snapshot_name)

        if snapobj:
            self._revert_to_snapshot(snapobj)

        else:
            raise VSphereManagerError("Snapshot not found.")

    def take_snapshot(self, vm, snapshot_name, description):
        """
        Create a new snapshot
        :param vm: {vim.VirtualMachine} The vm to create a snapshot of
        :param snapshot_name: {str} The snapshot name
        :param description: {str} Description of the snapshot
        """
        task = vm.CreateSnapshot(snapshot_name, description, False, False)
        self.wait_for_task(task)

    @staticmethod
    def get_vm_info(vm):
        """
        Get vm information
        :param vm: {vim.VirtualMachine} The vm
        :return: {dict} Vm info
        """
        return {
            "Name": vm.summary.config.name,
            "Template": vm.summary.config.template,
            "Path": vm.summary.config.vmPathName,
            "Guest": vm.summary.config.guestFullName,
            "Instance UUID": vm.summary.config.instanceUuid,
            "Bios UUID": vm.summary.config.uuid,
            "State": vm.summary.runtime.powerState,
            "VMware Tools": vm.summary.guest.toolsStatus,
            "Ip Address": vm.summary.guest.ipAddress,
        }

    @staticmethod
    def construct_csv(results):
        """
        Constructs a csv from results
        :param results: The results to add to the csv (results are list of flat dicts)
        :return: {list} csv formatted list
        """
        csv_output = []
        headers = reduce(set.union, list(map(set, list(map(dict.keys, results)))))

        csv_output.append(",".join(map(str, headers)))

        for result in results:
            csv_output.append(
                ",".join(
                    [
                        s.replace(",", " ")
                        for s in map(
                            str,
                            [str(result.get(h, None)).encode("utf-8") for h in headers],
                        )
                    ]
                )
            )

        return csv_output
