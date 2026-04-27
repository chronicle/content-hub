# ==============================================================================
# title           :FileRetentionManager.py
# description     :This Module helps to handle file retention.
# author          :itaih@siemplify.co
# date            :19-02-19
# python_version  :3.7
# product_version :????
# ==============================================================================

# =====================================
#              IMPORTS                #
# =====================================
from __future__ import annotations
import os
import shutil
import traceback
import datetime
import soar_sdk.SiemplifyUtils
import copy


class FolderTimeFormat:
    def __init__(self, date_time_format, datetime_attribute_name):
        self.date_time_format = date_time_format
        self.datetime_attribute_name = datetime_attribute_name


YEAR_FORMAT = "%Y"
MONTH_FORMAT = "%m"
DAY_FORMAT = "%d"
HOUR_FORMAT = "%H"

FOLDER_TREE_FORMAT = [
    FolderTimeFormat(YEAR_FORMAT, "year"),
    FolderTimeFormat(MONTH_FORMAT, "month"),
    FolderTimeFormat(DAY_FORMAT, "day"),
    FolderTimeFormat(HOUR_FORMAT, "hour"),
]


class FileRetentionManagerException(Exception):
    pass


class FileRetentionManager:
    def __init__(self, logger):
        """
        :param logger: {SiemplifyLogger.SiemplifyLogger}
        """
        self.LOGGER = logger

    def retensify_file(
        self,
        original_file_path,
        destination_folder,
        retention_limit_hours=24,
        retention_limit_disabled=False,
    ):
        """
        This method moves a file into a destination folder, under a hierichal time-based sub-folders structure (of Year-Month-Day-Hour: Files)
        Every time the method is called, the root destination folder is scanned, and folders older then the given retention time (relative to utc now) are deleted
        The purpose of the folder-structure is to improve scan performance in regard to a more straight forward single list scan. (IE: default retention for Error files is 14 days.
        Arcsight Creates CSV every 30 seconds. After 14 days, its ~40000 files.
        The connector is supposed to run every 1 second, but a 40K file scan is ~2 second long, and does resulting in a bottleneck)
        :param original_file_path: {string} The Original File path, that will be moved into the destination folder
        :param destination_folder: {string} The destination folder, that under it, in a heirarchical strucure files will be stored and deleted based on retention limit
        :param retention_limit_hours: {int} How long, relative to UTC now, allow a folder to be retained (In hours)
        :param retention_limit_disabled: {bool} If False, file will not be delted
        :return: None
        """
        try:
            retention_folder_path = FileRetentionManager.create_retention_folder_name(
                destination_folder
            )
            self.create_retention_folder_if_not_exists(retention_folder_path)

            self.move_file(original_file_path, retention_folder_path)

            if not retention_limit_disabled:
                self.delete_old_retention_folders(
                    destination_folder, retention_limit_hours
                )
            else:
                self.LOGGER.info(
                    "Retention limit disabled. Old files will not be deleted."
                )
        except Exception as e:
            self.LOGGER.error(f"Failed to retensify {original_file_path}")
            self.LOGGER.exception(e)

    @staticmethod
    def create_retention_folder_name(destination_folder):
        """
        Creates and returns the final destination sub-folder, based on a Year-Month-Day-Hour folder structure, under the desired root folder. Relative to UTC now
        :param destination_folder: {string} The root destination folder, underwhich a sub-folders heirarchy will be created
        :return: {string} The completed final folder-detination. IE: root\2004\04\28\16
        """
        now = SiemplifyUtils.utc_now()

        retention_folder_path = destination_folder

        for folder_format in FOLDER_TREE_FORMAT:
            retention_folder_path = os.path.join(
                retention_folder_path, now.strftime(folder_format.date_time_format)
            )

        return retention_folder_path

    def move_file(self, original_file_path, destination_folder):
        """
        Moves a file into a destination folder, with logs and error handling.
        :param original_file_path: {string}
        :param destination_folder: {string}
        :return: None
        """
        filename = os.path.basename(original_file_path)
        destination_path = os.path.join(destination_folder, filename)
        try:
            self.LOGGER.info(f"Moving {original_file_path} into {destination_folder}")
            shutil.move(original_file_path, destination_path)
        except Exception:
            raise FileRetentionManagerException(
                f"Failed to move file {original_file_path} to {destination_path}. Details: {traceback.format_exc()}"
            )

    def create_retention_folder_if_not_exists(self, folder_path):
        """
        Creates a folder, if it doesn't exists, if it alrleady exists as a file, raises an FileRetentionManagerException.
        Logs everything like a good boy
        :param folder_path: {string} The desired folder path to be validated or created
        :return: None
        """
        if os.path.exists(folder_path):
            if not os.path.isdir(folder_path):
                raise FileRetentionManagerException(
                    f"Cannot create folder {folder_path} as it already exist as a file"
                )
        else:
            os.makedirs(folder_path)
            self.LOGGER.info(
                f"Created Directory {folder_path} as it does not exist yet"
            )

    def delete_old_retention_folders(self, root_folder, retention_hours):
        """
        Deletes old folders in a time-based hierarchical structure, in referance to utc now. The folder tree is expected to be created by the FileRetentionManager, by the retensify_file method
        :param root_folder: {string} The retention folder tree root. For example, and ERROR or DONE folder.
        :param retention_hours: {int} States how many hours back, relative to utc now to keep. All older files will be deleted
        :return:
        """
        now = SiemplifyUtils.unix_now()
        retention_limit = now - (
            (int(retention_hours)) * 60 * 60 * 1000
        )  # Convert hours to milliseconds
        retention_limit_dt = SiemplifyUtils.convert_unixtime_to_datetime(
            retention_limit
        )
        self._delete_old_retention_folders(
            root_folder, retention_limit_dt, copy.deepcopy(FOLDER_TREE_FORMAT)
        )

    def _delete_old_retention_folders(
        self,
        root_folder,
        retention_limit_dt,
        folder_names_tree_format=FOLDER_TREE_FORMAT,
    ):
        """
        Internal recursive implementation of the delete_old_retention_folders method.
        :param root_folder: {string} The current root level. With each recursive-call, the root folder will be one level deeper
        :param retention_limit_dt: {datetime.datetime} Indicating what the retention limit is. All folders older then it, will be deleted
        :param folder_names_tree_format: { List of FileRetentionManager.FolderTimeFormat} This list of time-format metadata objects, helps parsing the names of the folders,
         into a Datetime object. Each value represents a level within the time-based hierarchy tree. With each recursive-call, the list shrinks.
        :return: None
        """

        self.LOGGER.info(
            f"Will now delete folders older then {retention_limit_dt} inside {root_folder}"
        )

        if len(folder_names_tree_format) < 1:
            # The number of items inside folder_names_tree_format should match the remaining number of expected folder levels. (Year-Month-day-Hour, 4 total levels)
            # With each dwelve, the first item in the format list is popped. If we start at the top, with 4 items, we expect to finish the last level with 1 remaining.
            raise FileRetentionManagerException(
                "folder_names_tree_format item count should be 1 or higher"
            )

        current_level_format_index = (
            0  # the first level, indicates what the current sub-folders format is
        )
        current_level_metadata = folder_names_tree_format.pop(
            current_level_format_index
        )  # remove the current sub-folders format before passing the tree-format to a deeper recusrion level
        current_level_time_format = (
            current_level_metadata.date_time_format
        )  # retrieve the datetime string format used to parse the folder name into Datetime object
        current_level_attribute = (
            current_level_metadata.datetime_attribute_name
        )  # retreive the datetime attribute name, corresponding to the current level & format.
        # * About the .pop: Teorethicly, tree_format is passed bewteen recurrsion as a reference, and that may lead to over-popping, resulting in a higher branch that will work with an over-popped list (that was popped by a deeper level).
        # But - it wont happen - because there can be only 1 dwelve Equal Match per level.
        # Clarification: There can be multiple older folders (which will be deleted), or multiple newer folders, which will be ignored. But only one matching folder.

        # Retreive the datetime attribute name, corresponding to the current level & format.
        retention_limit_current_value = retention_limit_dt.__getattribute__(
            current_level_attribute
        )

        # For each Sub folder in the current level
        for sub_item in os.listdir(root_folder):
            sub_item_path = os.path.join(root_folder, sub_item)

            try:
                # Validate it's a folder. Files are ignored, and will be
                # automatically deleted as part of the folder deletion:
                if os.path.isdir(sub_item_path):
                    try:
                        current_folder_datetime = datetime.datetime.strptime(
                            sub_item, current_level_time_format
                        )
                    except Exception:
                        self.LOGGER.error(
                            f"Folder {sub_item} is not in the format {current_level_time_format}. Skipping folder."
                        )
                        continue

                    current_folder_compare_value = (
                        current_folder_datetime.__getattribute__(
                            current_level_attribute
                        )
                    )
                    current_folder_path = os.path.join(root_folder, sub_item)

                    # Delete folders that are older then the retention limit
                    if current_folder_compare_value < retention_limit_current_value:
                        try:
                            # Complete deletion with all sub-files
                            shutil.rmtree(current_folder_path)
                            self.LOGGER.info(
                                f"Folder deleted: {current_folder_path} is before the retention limit of {retention_limit_dt}"
                            )
                        except Exception as e:
                            self.LOGGER.error(
                                f"Failed to delete folder {current_folder_path}"
                            )
                            self.LOGGER.exception(e)
                    # Ignore folders that are newer then the retention limit
                    # (practically, there shouldn't be any):
                    elif current_folder_compare_value > retention_limit_current_value:
                        self.LOGGER.info(
                            f"Folder untouched: {current_folder_path} is after the retention limit of {retention_limit_dt}"
                        )
                    # Dwelve deeper and folder match - those who represent the
                    # current time
                    elif not len(folder_names_tree_format):
                        # If we are at last level but the value of the folder
                        # is equal to the limit, don't dive deeper (last level)
                        # just continue.
                        continue
                    else:
                        self._delete_old_retention_folders(
                            current_folder_path,
                            retention_limit_dt,
                            folder_names_tree_format,
                        )

            except Exception as e:
                self.LOGGER.error(f"Unable to retensify {sub_item_path}. Skipping.")
                self.LOGGER.exception(e)
