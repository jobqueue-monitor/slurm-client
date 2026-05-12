from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import ProgressBar, Static


def _color(percent: float) -> str:
    if percent < 50:
        return "green"
    elif 50 < percent < 80:
        return "yellow"
    else:
        return "red"


class ResourceBar(Widget):
    # total/taken/percentage
    # additional info: unit (if not a count)
    #
    # display options:
    # 1. table containing total / taken / taken %
    # 2. bar with max / taken indicators (similar to htop)
    DEFAULT_CSS = """
    ResourceBar {
        border: solid red;
    }

    ResourceBar ProgressBar {
        padding: 0 2 0 2;
    }

    ResourceBar Bar > .bar--bar {
        color: $primary;
        background: $primary 30%;
    }
    """

    used = reactive(0.0)

    def compose(self) -> ComposeResult:
        with Horizontal():
            yield ProgressBar(id="bar", show_eta=False, show_percentage=False)
            yield Static("", id="label")

    def __init__(self, used: float, total: float, units: str | None, **kwargs):
        super().__init__(**kwargs)

        self.used = used
        self.total = total

        self.units = units

    def on_mount(self):
        bar = self.query_one("ProgressBar#bar")
        bar.total = self.total
        bar.progress = self.used

    async def watch_used(self) -> None:
        if self.total == 0:
            return

        percentage = self.used / self.total

        bar = self.query_one("ProgressBar#bar")
        label = self.query_one("Static#label")

        bar.update(progress=self.used)

        if self.units is not None:
            progress_label = (
                f"{self.used:.1f} {self.units} / {self.total:.1f} {self.units}"
            )
        else:
            progress_label = f"{int(self.used)} / {int(self.total)}"

        label.update(f"{percentage * 100:.0f}% ({progress_label})")
        color = _color(percentage)

        bar_widget = bar.query_one("Bar")
        bar_widget.styles.color = color
        bar_widget.styles.background = f"{color} 30%"


if __name__ == "__main__":
    from textual.app import App

    class ResourceApp(App):
        def compose(self):
            yield ResourceBar(used=0.0, total=10.0, units=None)

        def increment(self):
            bar = self.query_one(ResourceBar)
            if bar.used < bar.total:
                bar.used += 1

        def on_mount(self):
            self.set_interval(0.5, self.increment)

    app = ResourceApp()
    app.run()
