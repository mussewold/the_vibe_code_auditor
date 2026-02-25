from pathlib import Path

from src.graph import graph


def render_graph(output_path: str | None = None) -> Path:
    """
    Tool function: render the LangGraph as a Mermaid-based PNG.

    - Uses `graph.get_graph().draw_mermaid_png()`.
    - Saves the image to the repository root by default.
    - Returns the `Path` to the written file.
    """

    if output_path is None:
        output_path = "graph.png"

    out = Path(output_path)

    png_bytes = graph.get_graph().draw_mermaid_png()
    out.write_bytes(png_bytes)

    return out


def main() -> None:
    """
    CLI entrypoint so this tool can be run with:

        uv run -m src.tools.render_graph
    """

    out = render_graph()
    print(f"Graph saved to {out.resolve()}")


if __name__ == "__main__":
    main()

