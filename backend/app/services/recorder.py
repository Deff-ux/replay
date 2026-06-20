import asyncio, ast
class TestRecorder:
    @staticmethod
    async def start_recording(url: str, output_path: str, env_config: dict):
        process = await asyncio.create_subprocess_exec("playwright", "codegen", "--target", "python", "--output", output_path, url)
        return process.pid
    @staticmethod
    async def parse_recorded_file(file_path: str) -> list[dict]:
        content = open(file_path, encoding="utf-8").read(); steps = []
        for node in ast.walk(ast.parse(content)):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                action = node.func.attr
                if action in {"goto", "click", "fill", "press"}:
                    args = [getattr(a, "value", None) for a in node.args]
                    steps.append({"action_type": "keypress" if action == "press" else action, "selector": args[0] if action != "goto" else None, "value": args[-1], "description": action})
        return steps
