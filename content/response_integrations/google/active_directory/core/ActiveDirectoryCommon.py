from __future__ import annotations
class ActiveDirectoryCommon:
    def __init__(self, siemplify_logger):
        self.siemplify_logger = siemplify_logger

    def process_custom_query_fields(self, custom_query_fields):
        """
        Process custom fields provided in action call
        :param custom_query_fields: {str}
        :return: {list} comma separated list of custom fields
        """
        result = []
        if not custom_query_fields:
            return result
        try:
            result = [field.strip() for field in custom_query_fields.split(",")]
        except Exception as e:
            self.siemplify_logger.error(
                f"Unable to process custom query fields:{custom_query_fields}"
            )
            self.siemplify_logger.exception(e)
        return result
