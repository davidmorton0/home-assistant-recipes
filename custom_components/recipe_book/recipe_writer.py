import re

_NEEDS_QUOTING = re.compile(r"[:#&*!|>'\"%@`\[\]\{\},]")


class RecipeWriter:
    def call(self, path, recipe):
        with open(path, "w") as f:
            f.write(self._to_yaml(recipe))

    def _to_yaml(self, recipe):
        lines = [
            f"- uuid: {recipe['uuid']}",
            f"  name: {self._yaml_str(recipe['name'])}",
            f"  category: {self._yaml_str(recipe['category'])}",
            f"  serves: {recipe['serves']}",
            f"  status: {self._yaml_str(recipe['status'])}",
            "  ingredients:",
        ]
        for item in recipe["ingredients"]:
            lines.append(f"    - {self._yaml_str(item)}")
        lines.append("  steps:")
        for item in recipe["steps"]:
            lines.append(f"    - {self._yaml_str(item)}")
        return "\n".join(lines) + "\n"

    def _yaml_str(self, value):
        if _NEEDS_QUOTING.search(value) or value.strip() != value:
            return '"' + value.replace('\\', '\\\\').replace('"', '\\"') + '"'
        return value
