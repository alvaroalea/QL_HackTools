#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QL Bitmap Viewer - PyQt6
Visualizador/inspector de memoria gráfica para Sinclair QL y datos binarios.

Modos:
  1: cada bit del fichero es un píxel.
  4: formato QL MODE 4 (512x256, 2 bits/píxel).
  8: formato QL MODE 8 (256x256, 4 bits/píxel).

El visor NO escala la imagen para adaptarla a la ventana.
El zoom es un múltiplo entero y la navegación vertical avanza de BYTE en BYTE.
"""

import sys
from pathlib import Path

from PyQt6.QtCore import Qt, QRect, QSize, pyqtSignal, QTimer
from PyQt6.QtGui import QColor, QImage, QPainter, QValidator
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QFileDialog, QHBoxLayout, QVBoxLayout,
    QSpinBox, QLineEdit, QPushButton, QLabel,
    QComboBox, QScrollBar, QMessageBox, QSizePolicy, QStatusBar
)

# Paleta QL estándar.

QL8 = [
    (0, 0, 0),       # 0 negro
    (0, 0, 255),     # 1 azul
    (255, 0, 0),     # 2 rojo
    (255, 0, 255),   # 3 magenta
    (0, 255, 0),     # 4 verde
    (0, 255, 255),   # 5 cian
    (255, 255, 0),   # 6 amarillo
    (255, 255, 255), # 7 blanco
]

QL4 = [
    (0, 0, 0),       # 00
    (255, 0, 0),     # 01 -> rojo
    (0, 255, 0),     # 10 -> verde
    (255, 255, 255), # 11 -> blanco
]


class NumberEdit(QLineEdit):
    """Campo numérico que acepta decimal y hexadecimal (0x1234 o $1234)."""
    valueChanged = pyqtSignal(int)

    def __init__(self, value=0, parent=None):
        super().__init__(parent)
        self.set_value(value)
        self.editingFinished.connect(self._emit_value)

    def set_value(self, value):
        self.setText(str(int(value)))

    def value(self):
        text = self.text().strip().lower()
        if not text:
            return 0
        if text.startswith("0x"):
            return int(text, 16)
        if text.startswith("$"):
            return int(text[1:], 16)
        return int(text, 10)

    def _emit_value(self):
        try:
            self.valueChanged.emit(self.value())
            self.setStyleSheet("")
        except ValueError:
            self.setStyleSheet("border: 2px solid red;")


class HexSpinBox(QSpinBox):
    """QSpinBox con entrada decimal y hexadecimal (0x... o $...)."""
    def __init__(self, value=0, parent=None):
        super().__init__(parent)
        self.setRange(-2147483647, 2147483647)
        self.setValue(value)
        self.setAccelerated(True)

    def valueFromText(self, text):
        text = text.strip().lower()
        try:
            if text.startswith("-0x"):
                return -int(text[3:], 16)
            if text.startswith("-$"):
                return -int(text[2:], 16)
            if text.startswith("0x"):
                return int(text[2:], 16)
            if text.startswith("$"):
                return int(text[1:], 16)
            return int(text, 10)
        except ValueError:
            return self.value()

    def textFromValue(self, value):
        return str(value)

    def validate(self, text, pos):
        text = text.strip().lower()
        if text in ("", "-", "+", "$", "0x", "-$", "-0x"):
            return (QValidator.State.Intermediate, text, pos)
        try:
            self.valueFromText(text)
            return (QValidator.State.Acceptable, text, pos)
        except ValueError:
            return (QValidator.State.Invalid, text, pos)


class BitmapWidget(QWidget):
    """Lienzo que muestra el bitmap a tamaño natural * zoom."""
    resized = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.image = QImage()
        self.zoom = 2
        self.setMouseTracking(True)
        self.setAutoFillBackground(True)

    def set_image(self, image):
        self.image = image
        self.updateGeometry()
        self.update()

    def set_zoom(self, zoom):
        self.zoom = max(1, int(zoom))
        self.updateGeometry()
        self.update()

    def sizeHint(self):
        if self.image.isNull():
            return QSize(640, 480)
        return QSize(self.image.width() * self.zoom,
                     self.image.height() * self.zoom)

    def minimumSizeHint(self):
        return QSize(100, 100)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.resized.emit()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(event.rect(), QColor(35, 35, 35))
        if self.image.isNull():
            painter.setPen(Qt.GlobalColor.lightGray)
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter,
                             "Seleccione un fichero binario")
            return

        target = QRect(0, 0,
                       self.image.width() * self.zoom,
                       self.image.height() * self.zoom)
        # Sin suavizado: cada píxel QL se ve como un bloque perfectamente nítido.
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, False)
        painter.drawImage(target, self.image)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sinclair QL Bitmap Inspector")
        self.resize(1200, 800)

        # Estado. Debe existir ANTES de que cualquier señal pueda dispararse.
        self.data = b""
        self.filename = ""
        self.rendered_start = 0
        self._offset_prev = 0

        self._build_ui()
        self._connect()

        self._offset_prev = self._safe_value(self.offset_edit)
        self._update_width_step()
        self._configure_position_range()
        self._render()

    # ---------- UI ----------
    def _build_ui(self):
        central = QWidget(self)
        self.setCentralWidget(central)
        root = QVBoxLayout(central)

        stretch = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        # Fila 1: fichero
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Fichero:"))
        self.file_edit = QLineEdit()
        self.file_edit.setReadOnly(True)
        self.file_edit.setSizePolicy(stretch)
        row1.addWidget(self.file_edit)
        self.open_btn = QPushButton("Abrir...")
        row1.addWidget(self.open_btn)
        root.addLayout(row1)

        # Fila 2: zoom, ancho, modo
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Zoom:"))
        self.zoom = QSpinBox()
        self.zoom.setRange(1, 32)
        self.zoom.setValue(2)
        row2.addWidget(self.zoom)

        row2.addWidget(QLabel("Ancho:"))
        self.width_edit = HexSpinBox(512)
        self.width_edit.setRange(1, 16384)
        self.width_edit.setToolTip(
            "Ancho de la imagen en píxeles:\n"
            "En MODE 4 debe ser múltiplo de 8;\n"
            "en MODE 8, múltiplo de 4."
        )
        row2.addWidget(self.width_edit)

        row2.addWidget(QLabel("Modo:"))
        self.mode = QComboBox()
        self.mode.addItem("1 - bitmap (1 bit/píxel)", 1)
        self.mode.addItem("4 - QL MODE 4 (2 bits/píxel)", 4)
        self.mode.addItem("8 - QL MODE 8 (4 bits/píxel)", 8)
        row2.addWidget(self.mode)
        row2.addStretch(1)
        root.addLayout(row2)

        # Fila 3: offset, posición inicial
        row3 = QHBoxLayout()
        row3.addWidget(QLabel("Offset:"))
        self.offset_edit = HexSpinBox(0)
        self.offset_edit.setToolTip(
            "Valor de referencia fijo (p.ej. la dirección de memoria real\n"
            "donde se cargaría el fichero). No cambia lo que hay en el\n"
            "fichero, solo cómo se interpreta 'Inicio'.\n"
            "Acepta decimal, 0x... y $..."
        )
        row3.addWidget(self.offset_edit)

        row3.addWidget(QLabel("Inicio:"))
        self.position_edit = HexSpinBox(0)
        self.position_edit.setToolTip(
            "Posición mostrada, en el rango [Offset, Offset + tamaño del fichero].\n"
            "La imagen comienza a leerse en el byte Inicio - Offset del fichero."
        )
        row3.addWidget(self.position_edit)

        self.save_btn = QPushButton("Guardar")
        self.save_btn.setToolTip("Guarda como PNG la imagen que se está visualizando ahora mismo.")
        row3.addWidget(self.save_btn)

        row3.addStretch(1)
        root.addLayout(row3)

        # Fila 4: lienzo + barra de desplazamiento
        view_row = QHBoxLayout()
        self.canvas = BitmapWidget()
        view_row.addWidget(self.canvas, 1)
        self.scroll = QScrollBar(Qt.Orientation.Vertical)
        view_row.addWidget(self.scroll)
        root.addLayout(view_row, 1)

        self.setStatusBar(QStatusBar(self))

    def _connect(self):
        self.open_btn.clicked.connect(self.open_file)
        self.save_btn.clicked.connect(self.save_image)

        self.zoom.valueChanged.connect(self._on_zoom)
        self.mode.currentIndexChanged.connect(self._on_mode_changed)
        self.width_edit.valueChanged.connect(self._on_parameter_changed)
        self.offset_edit.valueChanged.connect(self._on_offset_changed)
        self.position_edit.valueChanged.connect(self._on_position_changed)

        # Inicio y la barra de desplazamiento comparten la misma escala
        # absoluta [Offset, Offset + tamaño del fichero].
        self.scroll.valueChanged.connect(self._on_scroll)
        self.canvas.resized.connect(self._on_canvas_resized)

    # ---------- Numeric/navigation ----------
    def _safe_value(self, edit, default=0):
        try:
            return edit.value()
        except (ValueError, TypeError):
            return default

    def _on_position_changed(self, *_):
        self._sync_scroll_from_position()
        self._render()

    def _on_scroll(self, value):
        self.position_edit.blockSignals(True)
        self.position_edit.setValue(value)
        self.position_edit.blockSignals(False)
        self._render()

    def _sync_scroll_from_position(self):
        value = self._safe_value(self.position_edit)
        self.scroll.blockSignals(True)
        self.scroll.setValue(value)
        self.scroll.blockSignals(False)

    def _on_offset_changed(self, *_):
        # Offset es un valor de referencia: al cambiarlo, el rango de Inicio
        # y de la barra se recalculan, pero la vista actual sobre el
        # fichero (Inicio - Offset) se mantiene fija en la medida de lo posible.
        old_offset = self._offset_prev
        start = self._safe_value(self.position_edit) - old_offset

        self._offset_prev = self._safe_value(self.offset_edit)
        new_offset = self._offset_prev

        size = len(self.data) if self.data else 0
        start = max(0, min(size, start))

        self._configure_position_range()

        self.position_edit.blockSignals(True)
        self.position_edit.setValue(new_offset + start)
        self.position_edit.blockSignals(False)

        self._sync_scroll_from_position()
        self._render()

    def _on_canvas_resized(self):
        if self.isVisible():
            QTimer.singleShot(0, self._render)

    # ---------- File ----------
    def open_file(self):
        filename, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar fichero binario", "",
            "Todos los archivos (*)"
        )
        if not filename:
            return

        try:
            self.data = Path(filename).read_bytes()
        except OSError as e:
            QMessageBox.critical(self, "Error", f"No se pudo leer el archivo:\n{e}")
            return

        self.filename = filename
        self.file_edit.setText(filename)

        # Al abrir, la vista comienza en el principio del fichero, es decir
        # Inicio = Offset (para que Inicio - Offset = 0).
        offset = self._safe_value(self.offset_edit)
        self._offset_prev = offset
        self._configure_position_range()

        self.position_edit.blockSignals(True)
        self.position_edit.setValue(offset)
        self.position_edit.blockSignals(False)

        self._sync_scroll_from_position()
        self._render()

    def save_image(self):
        if self.canvas.image.isNull():
            QMessageBox.information(
                self, "Guardar imagen",
                "No hay ninguna imagen que guardar todavía."
            )
            return

        suggested = "captura.png"
        if self.filename:
            suggested = Path(self.filename).stem + ".png"

        filename, _ = QFileDialog.getSaveFileName(
            self, "Guardar imagen como PNG", suggested,
            "Imagen PNG (*.png)"
        )
        if not filename:
            return

        if not filename.lower().endswith(".png"):
            filename += ".png"

        if not self.canvas.image.save(filename, "PNG"):
            QMessageBox.critical(self, "Error", f"No se pudo guardar la imagen en:\n{filename}")
        else:
            self.statusBar().showMessage(f"Imagen guardada en {filename}", 5000)

    # ---------- Parameters ----------
    def _on_zoom(self, value):
        self.canvas.set_zoom(value)
        self._render()

    def _on_parameter_changed(self, *_):
        self._configure_position_range()
        self._render()

    def _on_mode_changed(self, *_):
        self._update_width_step()
        self._on_parameter_changed()

    def _update_width_step(self):
        # Modo 1 y modo 4 empaquetan 8 píxeles por unidad de línea;
        # modo 8 empaqueta 4 píxeles por unidad de línea.
        mode = self._mode()
        step = 4 if mode == 8 else 8
        self.width_edit.setSingleStep(step)

    def _mode(self):
        data = self.mode.currentData()
        return int(data) if data is not None else 1

    def _bytes_per_line(self):
        width = max(1, self._safe_value(self.width_edit, 512))
        mode = self._mode()

        if mode == 1:
            # 8 bits por byte
            return max(1, (width + 7) // 8)
        if mode == 4:
            # QL MODE 4: 2 bytes -> 8 pixels
            return max(1, (width + 7) // 8 * 2)
        # QL MODE 8: 2 bytes -> 4 pixels
        return max(1, (width + 3) // 4 * 2)

    def _line_count(self):
        zoom = max(1, self.zoom.value())
        return max(1, self.canvas.height() // zoom)

    def _configure_position_range(self):
        # Offset es la referencia fija; Inicio y la barra se mueven en el
        # rango [Offset, Offset + tamaño del fichero]. Navegación byte a byte.
        offset = self._safe_value(self.offset_edit)
        size = len(self.data) if self.data else 0
        lo, hi = offset, offset + size

        self.position_edit.blockSignals(True)
        self.position_edit.setRange(lo, hi)
        self.position_edit.blockSignals(False)

        self.scroll.blockSignals(True)
        self.scroll.setRange(lo, hi)
        self.scroll.setSingleStep(1)
        self.scroll.setPageStep(max(1, self._bytes_per_line()))
        self.scroll.blockSignals(False)

    # ---------- QL decoding ----------
    @staticmethod
    def _mode1_pixel(data, byte_index, bit):
        if byte_index < 0 or byte_index >= len(data):
            return 0
        return 1 if (data[byte_index] & (0x80 >> bit)) else 0

    @staticmethod
    def _ql4_pixel(data, pair_index, pixel):
        """QL MODE 4: byte G seguido de byte R; MSB es el píxel izquierdo."""
        i = pair_index
        if i < 0 or i + 1 >= len(data):
            return 0
        g = 1 if (data[i] & (0x80 >> pixel)) else 0
        r = 1 if (data[i + 1] & (0x80 >> pixel)) else 0
        return (g << 1) | r

    @staticmethod
    def _ql8_pixel(data, pair_index, pixel):
        """QL MODE 8: GFGFGFGF seguido de RBRBRBRB."""
        i = pair_index
        if i < 0 or i + 1 >= len(data):
            return 0

        # En GFGFGFGF, las posiciones pares contienen G y las impares F.
        # En RBRBRBRB, las posiciones pares contienen R y las impares B.
        # El 'pixel' QL 0..3 se corresponde con bits 7,5,3,1.
        bitmask = 0x80 >> (pixel * 2)
        g = 1 if (data[i] & bitmask) else 0
        r = 1 if (data[i + 1] & bitmask) else 0
        b = 1 if (data[i + 1] & (bitmask >> 1)) else 0
        return (r << 1) | (g << 2) | b

    def _decode_image(self, start, width, height, mode):
        if width <= 0 or height <= 0:
            return QImage()

        # Evita que un ancho gigantesco consuma memoria accidentalmente.
        width = min(width, 16384)
        height = min(height, 16384)

        image = QImage(width, height, QImage.Format.Format_RGB32)
        image.fill(QColor(*QL8[0]))

        # Las líneas se almacenan consecutivamente en el fichero.
        if mode == 1:
            bpl = (width + 7) // 8
            for y in range(height):
                row = start + y * bpl
                for x in range(width):
                    bi = row + x // 8
                    bit = x & 7
                    on = self._mode1_pixel(self.data, bi, bit)
                    image.setPixelColor(x, y, QColor(255, 255, 255) if on else QColor(0, 0, 0))

        elif mode == 4:
            # 8 píxeles por cada par de bytes.
            pairs_per_line = (width + 7) // 8
            bpl = pairs_per_line * 2
            for y in range(height):
                row = start + y * bpl
                for pair in range(pairs_per_line):
                    i = row + pair * 2
                    for p in range(8):
                        x = pair * 8 + p
                        if x >= width:
                            break
                        c = self._ql4_pixel(self.data, i, p)
                        image.setPixelColor(x, y, QColor(*QL4[c]))

        else:
            # MODE 8: 4 píxeles por cada par de bytes.
            pairs_per_line = (width + 3) // 4
            bpl = pairs_per_line * 2
            for y in range(height):
                row = start + y * bpl
                for pair in range(pairs_per_line):
                    i = row + pair * 2
                    for p in range(4):
                        x = pair * 4 + p
                        if x >= width:
                            break
                        c = self._ql8_pixel(self.data, i, p)
                        # Tabla QL8: c = RGB bits; flash se ignora.
                        image.setPixelColor(x, y, QColor(*QL8[c]))

        return image

    # ---------- Rendering ----------
    @staticmethod
    def _fmt_hex(value):
        if value < 0:
            return f"{value} (-0x{-value:X})"
        return f"{value} (0x{value:X})"

    def _render(self):
        mode = self._mode()
        width = max(1, self._safe_value(self.width_edit, 512))
        offset = self._safe_value(self.offset_edit)
        position = self._safe_value(self.position_edit)

        # Regla solicitada: el gráfico comienza en Posición - Offset.
        start = position - offset

        # Permitimos offsets que apunten antes de 0: se muestran como bytes
        # negros/ausentes hasta alcanzar el fichero.
        visible_start = max(0, start)

        height = self._line_count()

        image = self._decode_image(visible_start, width, height, mode)

        self.rendered_start = start
        self.canvas.set_zoom(self.zoom.value())
        self.canvas.set_image(image)

        if self.data:
            end_file = min(len(self.data), visible_start + self._bytes_per_line() * height)
            bytes_shown = max(0, end_file - visible_start)
            range_end = position + bytes_shown - 1 if bytes_shown > 0 else position

            self.statusBar().showMessage(
                f"{Path(self.filename).name}  |  {len(self.data):,} bytes  |  "
                f"Altura {height} px  |  "
                f"Offset {self._fmt_hex(offset)}  |  "
                f"Inicio {self._fmt_hex(start)}  |  "
                f"Rango {self._fmt_hex(position)} – {self._fmt_hex(range_end)}"
            )
        else:
            self.statusBar().showMessage(
                f"Altura {height} px  |  "
                f"Offset {self._fmt_hex(offset)}  |  "
                f"Inicio {self._fmt_hex(start)}"
            )

    def closeEvent(self, event):
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("QL Bitmap Inspector")
    app.setApplicationDisplayName("Sinclair QL Bitmap Inspector")
    w = MainWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
