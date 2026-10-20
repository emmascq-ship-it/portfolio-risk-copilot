"""Render the LinkedIn cover using metrics from the bundled synthetic demo."""
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from risk_engine import calculate_risk, load_inputs
m = calculate_risk(*load_inputs(ROOT / 'sample_inputs')).metrics
im = Image.new('RGB', (1200, 627), '#102A43')
d = ImageDraw.Draw(im)
def font(size, bold=False):
    return ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial' + (' Bold' if bold else '') + '.ttf', size)
def text(x, y, value, size, color='#FFFFFF', bold=False):
    d.text((x, y), value, font=font(size, bold), fill=color)

d.rectangle((0, 0, 1200, 8), fill='#38C1B1')
text(60, 48, 'PYTHON  /  RISK ANALYTICS  /  AUTOMATION', 17, '#63D8C9', True)
text(60, 105, 'Portfolio Risk', 62, bold=True)
text(60, 174, 'Copilot', 62, bold=True)
text(60, 274, 'From portfolio data to a', 27, '#D8E5EC')
text(60, 311, 'review-ready risk brief.', 27, '#D8E5EC')
text(60, 395, 'VaR & Expected Shortfall', 21, bold=True)
text(60, 430, 'Factor exposures • Stress testing • Backtesting', 19, '#B8CDD8')
text(60, 510, 'Deterministic calculations. Evidence-grounded commentary.', 18, '#D8E5EC')
text(60, 540, 'Human review and escalation.', 18, '#D8E5EC')

d.rounded_rectangle((700, 90, 1140, 475), radius=18, fill='#F5F7F8')
text(727, 112, 'SYNTHETIC DEMO SNAPSHOT', 16, '#168C8C', True)
for y, label, value in [(159, 'Historical VaR · 95%', f"{m['historical_var_95']:.2%}"), (261, 'Expected Shortfall · 95%', f"{m['expected_shortfall_95']:.2%}"), (363, 'Worst stress scenario', f"{m['worst_stress_return']:.1%}")]:
    text(727, y, label, 18, '#607383')
    text(727, y + 28, value, 43, '#102A43', True)
    d.line((727, y + 86, 1111, y + 86), fill='#DCE3E8', width=1)
text(60, 592, 'INTERACTIVE STREAMLIT APPLICATION', 13, '#86A6B8', True)
text(760, 592, 'Synthetic data • Portfolio demonstration', 13, '#86A6B8')
im.save(ROOT / 'assets/linkedin-featured.png')
