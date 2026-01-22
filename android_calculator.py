from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.core.window import Window

# Optional: nicer default window size on desktop (ignored on Android)
Window.size = (360, 640)


class CalculatorUI(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", spacing=10, padding=12, **kwargs)

        # Display
        self.display = TextInput(
            text="0",
            font_size=40,
            readonly=True,
            halign="right",
            multiline=False,
            size_hint_y=None,
            height=100,
        )
        self.add_widget(self.display)

        # Buttons grid
        grid = GridLayout(cols=4, spacing=8)

        buttons = [
            ("C", self.clear), ("⌫", self.backspace), ("±", self.toggle_sign), ("/", self.add_op),
            ("7", self.add_digit), ("8", self.add_digit), ("9", self.add_digit), ("*", self.add_op),
            ("4", self.add_digit), ("5", self.add_digit), ("6", self.add_digit), ("-", self.add_op),
            ("1", self.add_digit), ("2", self.add_digit), ("3", self.add_digit), ("+", self.add_op),
            ("0", self.add_digit), (".", self.add_decimal), ("=", self.evaluate), ("%", self.percent),
        ]

        for label, handler in buttons:
            btn = Button(
                text=label,
                font_size=28,
                on_press=handler,
            )
            grid.add_widget(btn)

        self.add_widget(grid)

        # Track whether a result was just shown (so next digit starts fresh)
        self.just_evaluated = False

    def set_text(self, value: str) -> None:
        self.display.text = value

    def get_text(self) -> str:
        return self.display.text

    def clear(self, _btn) -> None:
        self.set_text("0")
        self.just_evaluated = False

    def backspace(self, _btn) -> None:
        if self.just_evaluated:
            self.set_text("0")
            self.just_evaluated = False
            return

        txt = self.get_text()
        txt = txt[:-1] if len(txt) > 1 else "0"
        # Keep valid "0" baseline
        if txt in ("", "-", "-0"):
            txt = "0"
        self.set_text(txt)

    def add_digit(self, btn) -> None:
        digit = btn.text
        txt = self.get_text()

        if self.just_evaluated:
            self.set_text(digit)
            self.just_evaluated = False
            return

        if txt == "0":
            self.set_text(digit)
        else:
            self.set_text(txt + digit)

    def add_decimal(self, _btn) -> None:
        txt = self.get_text()

        if self.just_evaluated:
            self.set_text("0.")
            self.just_evaluated = False
            return

        # Only allow one decimal in the current number chunk
        last_chunk = self._last_number_chunk(txt)
        if "." not in last_chunk:
            self.set_text(txt + ".")

    def add_op(self, btn) -> None:
        op = btn.text
        txt = self.get_text()

        if txt == "0" and op in ("*", "/", "+"):
            # Let "0+" etc. be okay, but prevent leading "*" or "/"
            if op in ("*", "/"):
                return

        if self.just_evaluated:
            self.just_evaluated = False

        # Replace trailing operator if user taps operators repeatedly
        if txt and txt[-1] in "+-*/":
            self.set_text(txt[:-1] + op)
        else:
            self.set_text(txt + op)

    def toggle_sign(self, _btn) -> None:
        txt = self.get_text()

        if self.just_evaluated:
            self.just_evaluated = False

        # Toggle sign on the last number chunk
        start, end, chunk = self._last_number_chunk_range(txt)
        if chunk == "" or chunk == "0":
            return

        if chunk.startswith("-"):
            new_chunk = chunk[1:]
        else:
            new_chunk = "-" + chunk

        new_txt = txt[:start] + new_chunk + txt[end:]
        self.set_text(new_txt)

    def percent(self, _btn) -> None:
        """
        Converts the last number chunk into chunk/100.
        Example: 50% -> 0.5, 200+10% -> 200+0.1
        """
        txt = self.get_text()
        if self.just_evaluated:
            self.just_evaluated = False

        start, end, chunk = self._last_number_chunk_range(txt)
        if chunk in ("", "-", ".", "-."):
            return

        try:
            val = float(chunk)
            val = val / 100.0
            # Compact formatting
            new_chunk = self._fmt_number(val)
            self.set_text(txt[:start] + new_chunk + txt[end:])
        except ValueError:
            pass

    def evaluate(self, _btn) -> None:
        expr = self.get_text()

        # Avoid eval on trailing operator
        if expr and expr[-1] in "+-*/":
            expr = expr[:-1]

        # Basic safety: allow only digits/operators/decimal/space/percent sign removed earlier
        allowed = set("0123456789+-*/.() ")
        if any(ch not in allowed for ch in expr):
            self.set_text("Error")
            self.just_evaluated = True
            return

        try:
            # Python eval handles operator precedence
            result = eval(expr, {"__builtins__": None}, {})
            self.set_text(self._fmt_number(result))
        except Exception:
            self.set_text("Error")

        self.just_evaluated = True

    # ---------- helpers ----------
    def _last_number_chunk(self, txt: str) -> str:
        _, _, chunk = self._last_number_chunk_range(txt)
        return chunk

    def _last_number_chunk_range(self, txt: str):
        """
        Returns (start_index, end_index, chunk_string) of the last number in the expression.
        Handles negatives like "-12.3" at the end or after an operator.
        """
        if not txt:
            return 0, 0, ""

        i = len(txt) - 1

        # Move left over digits/decimal
        while i >= 0 and (txt[i].isdigit() or txt[i] == "."):
            i -= 1

        # Handle negative sign for the chunk if it's a unary minus
        if i >= 0 and txt[i] == "-":
            # Unary if at beginning or preceded by an operator
            if i == 0 or txt[i - 1] in "+-*/(":
                i -= 1

        start = i + 1
        end = len(txt)
        return start, end, txt[start:end]

    def _fmt_number(self, n) -> str:
        try:
            # Convert ints like 5.0 -> 5
            if isinstance(n, float) and n.is_integer():
                return str(int(n))
            return str(n)
        except Exception:
            return "Error"


class AndroidCalculatorApp(App):
    def build(self):
        self.title = "Android Calculator (Prototype)"
        return CalculatorUI()


if __name__ == "__main__":
    AndroidCalculatorApp().run()
