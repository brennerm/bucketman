import rich.console
import rich.panel
import rich.repr
import rich.style
import rich.segment
import textual.reactive
import textual.widget
import textual.widgets

class VerticalDivider(textual.widget.Widget):
    name = 'vertical divider'
    def render(self) -> rich.console.RenderableType:
        segments = [rich.segment.Segment('▏')] * self.size.height
        return rich.segment.Segments(segments, new_lines=True)

