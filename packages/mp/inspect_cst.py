
import libcst as cst
from libcst.metadata import PositionProvider

code = r"""
def test_func():
    siemplify.LOGGER.error(
        f"An error occurred on entity: {entity.identifier}.\n{str(e)}."
    )

    other_func(1, 2) # Single line
"""


class AddTrailingCommaTransformer(cst.CSTTransformer):
    METADATA_DEPENDENCIES = (PositionProvider,)

    def leave_Call(self, original_node: cst.Call, updated_node: cst.Call) -> cst.Call:
        if not updated_node.args:
            return updated_node

        pos = self.get_metadata(PositionProvider, original_node)
        is_multiline = pos.start.line != pos.end.line

        if is_multiline:
            print(f"Found multiline call: {original_node.func}")
            last_arg = updated_node.args[-1]
            print(f"  last_arg.comma type: {type(last_arg.comma)}")
            if isinstance(last_arg.comma, cst.MaybeSentinel) or last_arg.comma is None:
                print("  Adding trailing comma")
                new_args = list(updated_node.args)
                new_args[-1] = last_arg.with_changes(comma=cst.Comma())
                return updated_node.with_changes(args=tuple(new_args))

        return updated_node


# Wrap module with metadata
wrapper = cst.metadata.MetadataWrapper(cst.parse_module(code))
transformer = AddTrailingCommaTransformer()
modified_tree = wrapper.visit(transformer)

print("\n--- Modified Code ---")
print(modified_tree.code)
