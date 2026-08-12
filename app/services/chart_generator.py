import io
from PIL import Image, ImageDraw, ImageFont
from app.models.bewertung import GesamtBewertung

class ChartGenerator:
    def generate_executive_summary_chart(self, bewertung: GesamtBewertung) -> io.BytesIO:
        """
        Generates the Executive Summary chart as a PNG image in memory.
        Features continuous red-yellow-green gradient bars with arrow tips, markers,
        scale labels, and criteria breakdown.
        """
        width = 1000
        # Calculate dynamic height based on number of categories and criteria
        num_categories = len(bewertung.kategorien)
        num_criteria = sum(len(c.kriterien) for c in bewertung.kategorien)
        
        # Base height for header + overall bar + scale labels + warning
        height = 180
        if bewertung.unter_50_prozent_warnung:
            height += 40
        height += num_categories * 80 + num_criteria * 26 + 40

        img = Image.new("RGB", (width, height), (255, 255, 255))
        draw = ImageDraw.Draw(img)

        try:
            font_title = ImageFont.load_default()
            font_bold = ImageFont.load_default()
            font_regular = ImageFont.load_default()
        except Exception:
            font_title = font_bold = font_regular = None

        y_cursor = 20

        # --- 1. Overall Header ---
        draw.text((30, y_cursor), f"Gesamtbewertung: {bewertung.gesamt_stufe_bezeichnung} ({bewertung.gesamt_prozent:.1f} %)", fill=(33, 37, 41), font=font_title)
        y_cursor += 25

        # Subtitle
        subtitle = f"Feldabdeckung: {bewertung.feldabdeckung_prozent:.1f} % | Bausteinabdeckung: {bewertung.bausteinabdeckung_prozent:.1f} %"
        draw.text((30, y_cursor), subtitle, fill=(108, 117, 125), font=font_regular)
        y_cursor += 30

        # --- 2. Overall Bar (Gesamtbalken) ---
        bar_left = 60
        bar_right = width - 60
        bar_width = bar_right - bar_left
        bar_height = 24
        
        # Draw Marker for Overall
        marker_x = bar_left + int((bewertung.gesamt_prozent / 100.0) * bar_width)
        marker_y = y_cursor
        # Marker Triangle pointing down
        draw.polygon([(marker_x - 8, marker_y), (marker_x + 8, marker_y), (marker_x, marker_y + 10)], fill=(0, 0, 0))
        # Value label above marker
        val_str = f"{bewertung.gesamt_prozent:.1f}%"
        draw.text((marker_x - 15, marker_y - 15), val_str, fill=(0, 0, 0), font=font_bold)
        
        bar_top = y_cursor + 12
        bar_bottom = bar_top + bar_height

        self._draw_gradient_bar(img, draw, bar_left, bar_top, bar_right, bar_bottom)

        y_cursor = bar_bottom + 10

        # Scale Labels (5 Stufen)
        labels = [
            ("Kritisch (0-20%)", 0.10),
            ("Mangelhaft (20-40%)", 0.30),
            ("Ausreichend (40-60%)", 0.50),
            ("Gut (60-80%)", 0.70),
            ("Sehr gut (80-100%)", 0.90)
        ]
        for label_text, pct in labels:
            lx = bar_left + int(pct * bar_width) - 40
            draw.text((lx, y_cursor), label_text, fill=(73, 80, 87), font=font_regular)

        y_cursor += 30

        # Warning line if incomplete coverage
        if bewertung.unter_50_prozent_warnung:
            warn_msg = "HINWEIS: Bausteine nicht vollständig erfasst. Bewertung bezieht sich nur auf erfasste Bereiche."
            if bewertung.nicht_erfasste_bausteine:
                warn_msg += f" (Fehlend: {', '.join(bewertung.nicht_erfasste_bausteine)})"
            draw.rectangle([(30, y_cursor), (width - 30, y_cursor + 28)], fill=(255, 243, 205), outline=(255, 230, 156))
            draw.text((40, y_cursor + 7), warn_msg, fill=(102, 77, 3), font=font_bold)
            y_cursor += 40

        # Horizontal Divider Line
        y_cursor += 10
        draw.line([(30, y_cursor), (width - 30, y_cursor)], fill=(222, 226, 230), width=2)
        y_cursor += 20

        # --- 3. Category Blocks ---
        for cat in bewertung.kategorien:
            # Category Name Left
            draw.text((30, y_cursor + 10), cat.bezeichnung, fill=(33, 37, 41), font=font_bold)
            
            # Category Gradient Bar Right
            c_bar_left = 450
            c_bar_right = width - 40
            c_bar_w = c_bar_right - c_bar_left
            c_bar_top = y_cursor + 15
            c_bar_bottom = c_bar_top + 18

            # Category Marker
            c_marker_x = c_bar_left + int((cat.prozent / 100.0) * c_bar_w)
            draw.polygon([(c_marker_x - 6, c_bar_top - 8), (c_marker_x + 6, c_bar_top - 8), (c_marker_x, c_bar_top - 1)], fill=(0, 0, 0))

            self._draw_gradient_bar(img, draw, c_bar_left, c_bar_top, c_bar_right, c_bar_bottom)
            
            # Cat Percentage text
            draw.text((c_bar_right + 5 if c_bar_right + 50 < width else c_bar_left - 60, c_bar_top), f"{cat.prozent:.1f}%", fill=(33, 37, 41), font=font_bold)

            y_cursor += 40

            # List Criteria under Category
            for kr in cat.kriterien:
                if not kr.ist_bewertet:
                    continue
                
                # Draw a filled bullet circle instead of unicode bullet character (prevents tofu box!)
                bullet_y = y_cursor + 4
                draw.ellipse([(50, bullet_y), (56, bullet_y + 6)], fill=(108, 117, 125))

                # Criteria Label (truncated to avoid overlap with points column)
                label_text = f"{kr.kriterium_id} ({kr.field_name})"
                if len(label_text) > 42:
                    label_text = label_text[:39] + "..."
                draw.text((65, y_cursor), label_text, fill=(73, 80, 87), font=font_regular)

                # Dedicated Right-Aligned Points Column at x=340
                pts_str = f"{kr.erreichte_punkte:.1f} / {kr.max_punkte:.1f} Pkt."
                draw.text((340, y_cursor), pts_str, fill=(33, 37, 41), font=font_bold)
                y_cursor += 24

            y_cursor += 15
            draw.line([(30, y_cursor), (width - 30, y_cursor)], fill=(233, 236, 239), width=1)
            y_cursor += 15

        output = io.BytesIO()
        img.save(output, format="PNG")
        output.seek(0)
        return output

    def _draw_gradient_bar(self, img: Image.Image, draw: ImageDraw.ImageDraw, left: int, top: int, right: int, bottom: int):
        """Draws a continuous Red -> Yellow -> Green horizontal gradient bar with arrow tips."""
        width = right - left
        height = bottom - top

        # Create 1D gradient line
        for x in range(width):
            pct = x / float(width)
            # Red (220, 53, 69) -> Yellow (255, 193, 7) -> Green (25, 135, 84)
            if pct < 0.5:
                t = pct / 0.5
                r = int(220 + (255 - 220) * t)
                g = int(53 + (193 - 53) * t)
                b = int(69 + (7 - 69) * t)
            else:
                t = (pct - 0.5) / 0.5
                r = int(255 + (25 - 255) * t)
                g = int(193 + (135 - 193) * t)
                b = int(7 + (84 - 7) * t)

            draw.line([(left + x, top), (left + x, bottom)], fill=(r, g, b))

        # Outline border
        draw.rectangle([(left, top), (right, bottom)], outline=(173, 181, 189), width=1)

chart_generator = ChartGenerator()
