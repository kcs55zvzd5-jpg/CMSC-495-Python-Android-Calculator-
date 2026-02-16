from __future__ import annotations

import re
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.core.window import Window
from kivy.graphics import Color, RoundedRectangle
from kivy.utils import get_color_from_hex

# Optional: nicer default window size on desktop (ignored on Android)
Window.size = (360, 640)
Window.clearcolor = get_color_from_hex("#000000")  # iPhone-style black background


# ---------------- I've updated the unary +/- and parentheis functions by using the Test Plan/Test cases ----------------
# ---------------- You should now be able to utilize the negative/positive buttons in a expression as intended ----------------

_NUM_RE = re.compile(
    r"""
    (?:
        (?:\d+(?:\.\d*)?)   # 12 or 12. or 12.3
      | (?:\.\d+)           # .5
    )
""",
    re.VERBOSE,
)


def _tokenize(expr: str):
    s = expr.replace(" ", "")
    tokens = []
    i = 0

    def prev_allows_unary():
        if not tokens:
            return True
        k, _ = tokens[-1]
        return (k == "op") or (k == "lparen")

    while i < len(s):
        ch = s[i]

        if ch == "(":
            tokens.append(("lparen", ch))
            i += 1
            continue
        if ch == ")":
            tokens.append(("rparen", ch))
            i += 1
            continue

        if ch == "%":  # postfix percent operator
            tokens.append(("op", "%"))
            i += 1
            continue

        if ch in "+-*/":
            if ch in "+-" and prev_allows_unary():
                tokens.append(("op", "u+" if ch == "+" else "u-"))
            else:
                tokens.append(("op", ch))
            i += 1
            continue

        m = _NUM_RE.match(s, i)
        if m:
            tokens.append(("num", float(m.group(0))))
            i = m.end()
            continue

        raise ValueError(f"Invalid character: {ch}")

    return tokens


def _to_rpn(tokens):
    # precedence: % > unary +/- > * / > + -
    prec = {"%": 4, "u+": 3, "u-": 3, "*": 2, "/": 2, "+": 1, "-": 1}
    right_assoc = {"u+", "u-"}

    output = []
    stack = []

    for kind, val in tokens:
        if kind == "num":
            output.append((kind, val))
        elif kind == "op":
            o1 = val
            while stack and stack[-1][0] == "op":
                o2 = stack[-1][1]
                if ((o1 in right_assoc and prec[o1] < prec[o2]) or
                        (o1 not in right_assoc and prec[o1] <= prec[o2])):
                    output.append(stack.pop())
                else:
                    break
            stack.append((kind, val))
        elif kind == "lparen":
            stack.append((kind, val))
        elif kind == "rparen":
            while stack and stack[-1][0] != "lparen":
                output.append(stack.pop())
            if not stack or stack[-1][0] != "lparen":
                raise ValueError("Mismatched parentheses")
            stack.pop()
        else:
            raise ValueError("Unknown token")

    while stack:
        if stack[-1][0] in ("lparen", "rparen"):
            raise ValueError("Mismatched parentheses")
        output.append(stack.pop())

    return output


def _eval_rpn(rpn):
    st = []
    for kind, val in rpn:
        if kind == "num":
            st.append(val)
            continue

        op = val

        if op == "%":  # percent fix after test plan : x% = x/100
            if not st:
                raise ValueError("Missing operand for %")
            x = st.pop()
            st.append(x / 100.0)
            continue

        if op in ("u+", "u-"):  # The unary +/- buttons
            if not st:
                raise ValueError("Missing operand for unary")
            x = st.pop()
            st.append(+x if op == "u+" else -x)
            continue

        if len(st) < 2:
            raise ValueError("Missing operand for binary")
        b = st.pop()
        a = st.pop()

        if op == "+":
            st.append(a + b)
        elif op == "-":
            st.append(a - b)
        elif op == "*":
            st.append(a * b)
        elif op == "/":
            if b == 0:
                raise ZeroDivisionError("Division by zero")
            st.append(a / b)
        else:
            raise ValueError("Unknown operator")

    if len(st) != 1:
        raise ValueError("Invalid expression")
    return st[0]


def evaluate_expression(expr: str) -> float:
    return _eval_rpn(_to_rpn(_tokenize(expr)))


def format_result(x: float) -> str:
    if abs(x - round(x)) < 1e-10:
        return str(int(round(x)))
    s = f"{x:.12f}".rstrip("0").rstrip(".")
    return s if s else "0"


# ---------------- This is just a little extra for fun. I made the buttons appearance more like a mobile calculator you'd see ----------------

class RoundButton(Button):
    
    def __init__(self, **kwargs):
        self.fill_color = kwargs.pop("fill_color", "#333333")
        super().__init__(**kwargs)

        # Remove default button background so we can draw our own
        self.background_normal = ""
        self.background_down = ""
        self.background_color = (0, 0, 0, 0)

        # Text styling
        self.color = get_color_from_hex("#FFFFFF")
        self.bold = True

        with self.canvas.before:
            self._c = Color(*get_color_from_hex(self.fill_color))
            self._r = RoundedRectangle(radius=[999])  # This makes the buttons more of a bubble instead of square boxes

        self.bind(pos=self._update_shape, size=self._update_shape)

    def _update_shape(self, *args):
        self._r.pos = self.pos
        self._r.size = self.size


class CalculatorUI(BoxLayout):
    """
    Top display area (history + main).
    """
    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", size_hint_y=None, height=170, spacing=6, **kwargs)

        self.history = Label(
            text="",
            font_size=18,
            halign="right",
            valign="middle",
            size_hint_y=None,
            height=45,
        )
        self.history.bind(size=lambda inst, _: setattr(inst, "text_size", inst.size))
        self.history.color = get_color_from_hex("#8E8E93")  # soft gray

        self.main = TextInput(
            text="0",
            font_size=56,
            readonly=True,
            halign="right",
            multiline=False,
            size_hint_y=None,
            height=115,
            background_normal="",
            background_active="",
        )
        self.main.foreground_color = get_color_from_hex("#FFFFFF")
        self.main.background_color = get_color_from_hex("#000000")
        self.main.cursor_color = get_color_from_hex("#000000")

        self.add_widget(self.history)
        self.add_widget(self.main)

    def set_history(self, text: str):
        self.history.text = text

    def set_main(self, text: str):
        self.main.text = text

    def get_main(self) -> str:
        return self.main.text


# ---------------- Calculator Logic + Layout ----------------

class AndroidCalculator(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", padding=14, spacing=12, **kwargs)

        # Draw a black background behind everything (matches iPhone vibe)
        with self.canvas.before:
            Color(*get_color_from_hex("#000000"))
            self._bg = RoundedRectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._update_bg, size=self._update_bg)

        self.display = CalculatorUI()
        self.add_widget(self.display)

        self.just_evaluated = False

        # Colors for button types
        self._colors = {
            "num": "#333333",   # numbers (dark gray)
            "func": "#A5A5A5",  # AC / % / ± / ⌫ (light gray)
            "op": "#FF9500",    # operators + equals (orange)
        }

        # AC / C button
        self.clear_btn = self._button("AC", self.clear, kind="func")

        # ---- MAIN KEYPAD LAYOUT ----
        self.keypad = BoxLayout(orientation="horizontal", spacing=10)

        # LEFT SIDE (numbers + functions)
        self.left_grid = GridLayout(cols=3, spacing=10, size_hint=(0.75, 1))

        left_buttons = [
            self.clear_btn,
            self._button("⌫", self.backspace, "func"),
            self._button("±", self.toggle_sign, "func"),

            self._button("7", self.add_digit, "num"),
            self._button("8", self.add_digit, "num"),
            self._button("9", self.add_digit, "num"),

            self._button("4", self.add_digit, "num"),
            self._button("5", self.add_digit, "num"),
            self._button("6", self.add_digit, "num"),

            self._button("1", self.add_digit, "num"),
            self._button("2", self.add_digit, "num"),
            self._button("3", self.add_digit, "num"),

            self._button("%", self.percent, "func"),
            self._button("0", self.add_digit, "num"),
            self._button(".", self.add_decimal, "num"),
        ]
        for b in left_buttons:
            self.left_grid.add_widget(b)

        # RIGHT SIDE (operators column INCLUDING "=")
        #This is to create a column for the opertors and color them. Just like you would see on an iphone or android mobile calculator
        self.right_col = BoxLayout(orientation="vertical", spacing=10, size_hint=(0.25, 1))

        right_buttons = [
            self._button("/", self.add_operator, "op"),
            self._button("*", self.add_operator, "op"),
            self._button("-", self.add_operator, "op"),
            self._button("+", self.add_operator, "op"),
            self._button("=", self.evaluate, "op"),
        ]
        for b in right_buttons:
            self.right_col.add_widget(b)

        self.keypad.add_widget(self.left_grid)
        self.keypad.add_widget(self.right_col)
        self.add_widget(self.keypad)

        # Resize buttons nicely when window changes
        self.bind(size=self._resize_buttons)
        self._resize_buttons()

    def _update_bg(self, *args):
        self._bg.pos = self.pos
        self._bg.size = self.size

    def _resize_buttons(self, *args):
        """
        Make buttons roughly square-ish based on available height.
        Works for both the left grid and the right operator column.
        """
        # available space below the display
        available_h = self.height - self.display.height - (self.padding[1] + self.padding[3]) - self.spacing
        available_h = max(available_h, 300)

        rows = 5
        gap = 10  # matches spacing
        btn_h = (available_h - gap * (rows - 1)) / rows
        btn_h = max(btn_h, 62)

        # Apply height to all buttons in both sections
        for child in list(self.left_grid.children) + list(self.right_col.children):
            child.size_hint_y = None
            child.height = btn_h

    # ---------- Button Factory ----------
    def _button(self, text, handler, kind="num"):
        btn = RoundButton(
            text=text,
            font_size=30 if text not in ("=", "AC") else 28,
            fill_color=self._colors.get(kind, "#333333"),
        )
        btn.bind(on_press=handler)
        return btn

    # ---------- Helpers ----------
    def _update_clear_label(self):
        self.clear_btn.text = "AC" if self.display.get_main() == "0" else "C"

    def _ends_with_operator(self, s: str) -> bool:
        return bool(s) and s[-1] in "+-*/"

    # ---------- Input ----------
    def add_digit(self, btn):
        value = btn.text
        current = self.display.get_main()

        if current == "Error":
            current = "0"

        if self.just_evaluated:
            self.display.set_main(value)
            self.display.set_history("")
            self.just_evaluated = False
        else:
            self.display.set_main(value if current == "0" else current + value)

        self._update_clear_label()

    def add_decimal(self, _):
        current = self.display.get_main()

        if current == "Error":
            self.display.set_main("0.")
            self.just_evaluated = False
            self._update_clear_label()
            return

        if self.just_evaluated:
            self.display.set_main("0.")
            self.display.set_history("")
            self.just_evaluated = False
            self._update_clear_label()
            return

        if self._ends_with_operator(current):
            self.display.set_main(current + "0.")
            self._update_clear_label()
            return

        last_break = max(
            current.rfind("+"),
            current.rfind("-"),
            current.rfind("*"),
            current.rfind("/"),
            current.rfind("("),
            current.rfind(")"),
        )
        segment = current[last_break + 1:] if last_break >= 0 else current
        if "." in segment:
            return

        self.display.set_main(current + ".")
        self._update_clear_label()

    def add_operator(self, btn):
        op = btn.text
        current = self.display.get_main()

        if current == "Error":
            return

        if self.just_evaluated:
            self.just_evaluated = False

        # replace trailing operator
        if self._ends_with_operator(current):
            current = current[:-1]

        if not current:
            current = "0"

        self.display.set_main(current + op)
        self.display.set_history(current + op)
        self._update_clear_label()

    def backspace(self, _):
        current = self.display.get_main()

        if current == "Error":
            self.display.set_main("0")
            self.just_evaluated = False
            self._update_clear_label()
            return

        self.display.set_main(current[:-1] if len(current) > 1 else "0")
        self.just_evaluated = False
        self._update_clear_label()

    def clear(self, _):
        self.display.set_main("0")
        self.display.set_history("")
        self.just_evaluated = False
        self._update_clear_label()

    # ---------- Sign Toggle: Utilizes parenthesis with the negative intergers (supports expression negatives like 0+(-5), 5-(-5)) ----------
    def toggle_sign(self, _):
        expr = self.display.get_main()

        if expr == "Error":
            return

        if self.just_evaluated:
            self.just_evaluated = False

        if self._ends_with_operator(expr):
            return

        has_percent = expr.endswith("%")
        core = expr[:-1] if has_percent else expr

        # If ends with "(-number)" -> unwrap to "number"
        m = re.search(r"\(\-(\d+(?:\.\d*)?|\.\d+)\)$", core)
        if m:
            start = m.start()
            number = m.group(1)
            new_core = core[:start] + number
            self.display.set_main((new_core + ("%" if has_percent else "")) if new_core else "0")
            self._update_clear_label()
            return

        # If ends with plain number -> wrap it as (-number) OR remove unary "-" like "*-5"
        m = re.search(r"(\d+(?:\.\d*)?|\.\d+)$", core)
        if not m:
            return

        start = m.start()
        number = m.group(1)

        # If it's already unary-negative like "...*-5" or "...+-5" -> remove unary minus
        if start > 0 and core[start - 1] == "-" and (start == 1 or core[start - 2] in "+-*/("):
            new_core = core[:start - 1] + number
        else:
            new_core = core[:start] + f"(-{number})"

        self.display.set_main(new_core + ("%" if has_percent else ""))
        self._update_clear_label()

    # ---------- Updated the Percent feature. ----------
    def percent(self, _):
        expr = self.display.get_main()

        if expr == "Error":
            return

        # Plain number => convert immediately (100 -> 1)
        if re.fullmatch(r"\s*[\+\-]?(?:\d+(?:\.\d*)?|\.\d+)\s*", expr):
            try:
                value = float(expr)
                self.display.set_main(format_result(value / 100.0))
                self._update_clear_label()
            except Exception:
                self.display.set_main("Error")
                self._update_clear_label()
            return

        # Expression => append postfix %
        if self._ends_with_operator(expr) or expr.endswith("%"):
            return

        self.display.set_main(expr + "%")
        self._update_clear_label()

    # ---------- Evaluate ----------
    def evaluate(self, _):
        expr = self.display.get_main()

        if expr == "Error":
            return

        if self._ends_with_operator(expr):
            self.display.set_main("Error")
            self._update_clear_label()
            return

        try:
            result = evaluate_expression(expr)
            self.display.set_history(expr)
            self.display.set_main(format_result(result))
            self.just_evaluated = True
            self._update_clear_label()
        except ZeroDivisionError:
            self.display.set_history(expr)
            self.display.set_main("Error")
            self.just_evaluated = True
            self._update_clear_label()
        except Exception:
            self.display.set_history(expr)
            self.display.set_main("Error")
            self.just_evaluated = True
            self._update_clear_label()


class AndroidCalculatorApp(App):
    def build(self):
        self.title = "Android Calculator"
        return AndroidCalculator()


if __name__ == "__main__":
    AndroidCalculatorApp().run()