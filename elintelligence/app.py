from __future__ import annotations

import html
import os
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QCloseEvent, QDesktopServices, QIcon, QKeyEvent, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from .chat_store import ChatMessage, ChatStore
from .llama_runtime import EngineConfig, LlamaServer, RuntimeInstaller
from .embeddings import EMBEDDING_MODEL_APPROX_MB, embedding_model_installed
from .models import CATALOG, ModelPreset, preset_by_id
from .paths import app_data_dir, resource_path
from .rag import RagStore
from .secret_store import SecretStore
from .settings_store import AppSettings, SettingsStore
from .workers import (
    ChatThread,
    EmbeddingModelDownloadThread,
    ModelDownloadThread,
    RagBatchImportThread,
    RagFolderSyncThread,
    RagReembedThread,
    RuntimeInstallThread,
)


APP_QSS = r"""
QMainWindow, QWidget#root {
    background: #070912;
    color: #EAF7FF;
    font-family: "Segoe UI";
    font-size: 10pt;
}
QFrame#sidebar, QFrame#chatPanel {
    background: #0D1320;
    border: 1px solid #173B4D;
    border-radius: 16px;
}
QFrame#headerPanel {
    background: #10182A;
    border: 1px solid #1EE7FF;
    border-radius: 16px;
}
QGroupBox {
    color: #A8BED7;
    font-weight: 600;
    border: 1px solid #1B4051;
    border-radius: 12px;
    margin-top: 10px;
    padding: 12px 8px 8px 8px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
    color: #7FF8FF;
}
QLabel#appTitle {
    font-size: 18pt;
    font-weight: 700;
    color: #F4FBFF;
}
QLabel#subtitle, QLabel#muted, QLabel#statusLabel {
    color: #91A8C2;
}
QLabel#sourceExcerpt {
    color: #AFC2D8;
    background: #09131F;
    border-left: 2px solid #1EE7FF;
    padding: 6px 8px;
    margin-bottom: 3px;
}
QLabel#statusLabel {
    background: #0A1421;
    border: 1px solid #184458;
    border-radius: 9px;
    padding: 7px;
}
QPushButton {
    background: #111F31;
    color: #EEF9FF;
    border: 1px solid #207B92;
    border-radius: 9px;
    padding: 7px 10px;
    font-weight: 600;
    min-height: 28px;
}
QPushButton:hover {
    background: #153249;
    border-color: #1EE7FF;
}
QPushButton:pressed {
    background: #0E5267;
}
QPushButton:disabled {
    color: #607487;
    border-color: #263743;
    background: #0D141D;
}
QPushButton#pinkButton {
    border-color: #AF328D;
}
QPushButton#pinkButton:hover {
    border-color: #FF2DD1;
    background: #30162D;
}
QLineEdit, QPlainTextEdit, QComboBox, QSpinBox {
    background: #080E18;
    color: #F2FAFF;
    border: 1px solid #24485B;
    border-radius: 8px;
    padding: 6px;
    selection-background-color: #0D7D93;
    min-height: 24px;
}
QComboBox QAbstractItemView {
    background: #0C1420;
    color: #F2FAFF;
    selection-background-color: #124B61;
    border: 1px solid #24485B;
}
QCheckBox {
    color: #EAF7FF;
    spacing: 7px;
}
QCheckBox::indicator {
    width: 16px;
    height: 16px;
}
QCheckBox::indicator:checked {
    background: #1EE7FF;
    border: 1px solid #7FF8FF;
}
QScrollArea {
    border: none;
    background: transparent;
}
QFrame#assistantBubble {
    background: #111D30;
    border: 1px solid #1B6178;
    border-radius: 14px;
}
QFrame#userBubble {
    background: #281428;
    border: 1px solid #8F347A;
    border-radius: 14px;
}
QLabel#bubbleTitle {
    color: #7FF8FF;
    font-weight: 700;
}
QFrame#userBubble QLabel#bubbleTitle {
    color: #FF8DE7;
}
QLabel#bubbleText {
    color: #F2F7FB;
    font-family: "Segoe UI";
    font-size: 10.5pt;
}
QPushButton#sourceButton {
    background: #091622;
    color: #A7FBFF;
    border: 1px solid #206B80;
    text-align: left;
    padding: 7px 9px;
}
QPushButton#sourceButton:hover {
    background: #103348;
    border-color: #1EE7FF;
}
QProgressBar {
    background: #080E18;
    border: 1px solid #24485B;
    border-radius: 6px;
    text-align: center;
    color: white;
}
QProgressBar::chunk {
    background: #1EE7FF;
    border-radius: 5px;
}
QSplitter::handle {
    background: #142536;
    width: 2px;
}
"""


class PromptEdit(QPlainTextEdit):
    send_requested = Signal()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            modifiers = event.modifiers()
            if not (modifiers & Qt.KeyboardModifier.ShiftModifier):
                self.send_requested.emit()
                event.accept()
                return
        super().keyPressEvent(event)



class ChatBubble(QFrame):
    def __init__(self, title: str, text: str, assistant: bool, sources: list[dict] | None = None):
        super().__init__()
        self.assistant = assistant
        self.setObjectName("assistantBubble" if assistant else "userBubble")
        self.setMaximumWidth(920)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 11)
        layout.setSpacing(7)

        self.title = QLabel(title)
        self.title.setObjectName("bubbleTitle")
        layout.addWidget(self.title)

        self.text_label = QLabel(text)
        self.text_label.setObjectName("bubbleText")
        self.text_label.setTextFormat(Qt.TextFormat.PlainText)
        self.text_label.setWordWrap(True)
        self.text_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.text_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self.text_label)

        self.sources_box = QVBoxLayout()
        self.sources_box.setSpacing(5)
        layout.addLayout(self.sources_box)
        self.set_sources(sources or [])

    def set_text(self, text: str) -> None:
        self.text_label.setText(text)

    def append_text(self, token: str) -> None:
        self.text_label.setText(self.text_label.text() + token)

    def set_sources(self, sources: list[dict]) -> None:
        while self.sources_box.count():
            item = self.sources_box.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        if not sources:
            return
        label = QLabel("FONTI · clicca per aprire")
        label.setObjectName("muted")
        self.sources_box.addWidget(label)
        for idx, src in enumerate(sources, 1):
            kind = str(src.get("kind") or ("web" if src.get("url") else "rag"))
            ref = str(src.get("ref") or (f"W{idx}" if kind == "web" else f"D{idx}"))
            title = str(src.get("title") or src.get("url") or src.get("path") or f"Fonte {idx}")
            page = src.get("page")
            suffix = f" · pag. {page}" if page else ""
            button = QPushButton(f"{ref}  ·  {title}{suffix}")
            button.setObjectName("sourceButton")

            if kind == "rag":
                path = str(src.get("path") or "")
                button.setToolTip(f"{path}{suffix}" if path else f"{title}{suffix}")
                button.clicked.connect(
                    lambda _checked=False, target=path, target_page=page: self._open_document(target, target_page)
                )
            else:
                url = str(src.get("url") or "")
                button.setToolTip(url)
                button.clicked.connect(lambda _checked=False, target=url: self._open_url(target))
            self.sources_box.addWidget(button)
            description = str(src.get("description") or "").strip()
            if kind == "rag" and description:
                excerpt = QLabel(description)
                excerpt.setObjectName("sourceExcerpt")
                excerpt.setWordWrap(True)
                excerpt.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
                self.sources_box.addWidget(excerpt)

    @staticmethod
    def _open_url(url: str) -> None:
        if url.startswith(("http://", "https://")):
            QDesktopServices.openUrl(QUrl(url))

    @staticmethod
    def _open_document(path: str, page: int | None = None) -> None:
        if not path:
            return
        file_path = Path(path)
        if not file_path.exists():
            return
        if file_path.suffix.lower() == ".pdf" and page:
            # Many browsers/PDF viewers understand the #page=N fragment. If the
            # registered Windows viewer ignores it, the document still opens and
            # the page number remains visible in the source button.
            url = QUrl.fromLocalFile(str(file_path))
            url.setFragment(f"page={page}")
            if QDesktopServices.openUrl(url):
                return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(file_path)))


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("ELintelligence")
        self.resize(1180, 780)
        self.setMinimumSize(900, 620)
        icon_path = resource_path("assets/icon.ico")
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        self.settings_store = SettingsStore()
        self.settings: AppSettings = self.settings_store.load()
        self.secret_store = SecretStore()
        self.chat_store = ChatStore()
        self.rag = RagStore()
        self.server = LlamaServer()
        self.runtime_installer = RuntimeInstaller()
        self.history: list[ChatMessage] = self.chat_store.load()
        self.worker = None
        self.current_assistant_bubble: ChatBubble | None = None
        self.current_answer = ""

        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(12, 12, 12, 12)
        root_layout.setSpacing(10)

        root_layout.addWidget(self._build_header())
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.sidebar_scroll = self._build_sidebar()
        self.chat_panel = self._build_chat_panel()
        self.splitter.addWidget(self.sidebar_scroll)
        self.splitter.addWidget(self.chat_panel)
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)
        self.splitter.setCollapsible(0, True)
        start_sidebar = max(195, min(225, int(self.settings.sidebar_width or 210)))
        self.splitter.setSizes([start_sidebar, 900])
        self.splitter.splitterMoved.connect(self._splitter_moved)
        if self.settings.sidebar_collapsed:
            self.sidebar_scroll.hide()
        root_layout.addWidget(self.splitter, 1)

        self.setStyleSheet(APP_QSS)
        self._refresh_models()
        self._sync_controls_from_settings()
        self._load_chat_ui()
        self._refresh_runtime_status()
        self._refresh_rag_status()
        self._folder_sync_queue: list[Path] = []
        QTimer.singleShot(1800, self._sync_watched_folders)
        self.folder_sync_timer = QTimer(self)
        self.folder_sync_timer.setInterval(300000)
        self.folder_sync_timer.timeout.connect(self._sync_watched_folders)
        self.folder_sync_timer.start()

    def _build_header(self) -> QWidget:
        frame = QFrame()
        frame.setObjectName("headerPanel")
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(14, 10, 14, 10)

        logo = QLabel()
        pixmap = QPixmap(str(resource_path("assets/icon.png")))
        if not pixmap.isNull():
            logo.setPixmap(pixmap.scaled(54, 54, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        layout.addWidget(logo)

        titles = QVBoxLayout()
        title = QLabel("ELintelligence")
        title.setObjectName("appTitle")
        subtitle = QLabel("AI locale per Windows · GGUF · Web opzionale · RAG documenti")
        subtitle.setObjectName("subtitle")
        titles.addWidget(title)
        titles.addWidget(subtitle)
        layout.addLayout(titles, 1)

        self.sidebar_toggle_btn = QPushButton("☰ Mostra controlli" if self.settings.sidebar_collapsed else "◀ Nascondi controlli")
        self.sidebar_toggle_btn.setMinimumWidth(136)
        self.sidebar_toggle_btn.clicked.connect(self._toggle_sidebar)
        layout.addWidget(self.sidebar_toggle_btn)

        self.status_label = QLabel("Pronto")
        self.status_label.setObjectName("statusLabel")
        self.status_label.setMinimumWidth(180)
        self.status_label.setMaximumWidth(360)
        layout.addWidget(self.status_label)
        return frame

    def _build_sidebar(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setMinimumWidth(195)
        scroll.setMaximumWidth(225)
        scroll.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)

        frame = QFrame()
        frame.setObjectName("sidebar")
        frame.setMinimumWidth(180)
        frame.setMaximumWidth(220)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Widget tecnici mantenuti come stato interno, ma spostati fuori dalla sidebar
        # per non costringerla ad allargarsi. Si modificano da Impostazioni avanzate.
        self.context_spin = self._spin(512, 32768, 4096, 512)
        self.tokens_spin = self._spin(64, 4096, 512, 64)
        self.gpu_spin = self._spin(0, 999, 99, 1)
        self.threads_spin = self._spin(1, 128, max(2, (os.cpu_count() or 4) - 1), 1)
        self.brave_key_edit = QLineEdit()
        self.brave_key_edit.setText(self.secret_store.load_brave_key())

        runtime_group = QGroupBox("Runtime")
        runtime_layout = QVBoxLayout(runtime_group)
        runtime_layout.setSpacing(6)
        self.backend_combo = QComboBox()
        self.backend_combo.addItem("Vulkan", "vulkan")
        self.backend_combo.addItem("CPU x64", "cpu")
        self.backend_combo.addItem("Custom", "custom")
        self.backend_combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.backend_combo.setMinimumContentsLength(8)
        self.backend_combo.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.backend_combo.currentIndexChanged.connect(self._save_settings_from_controls)
        runtime_layout.addWidget(self.backend_combo)

        self.install_runtime_btn = QPushButton("Installa")
        self.install_runtime_btn.clicked.connect(self._install_runtime)
        self.custom_server_btn = QPushButton("Server…")
        self.custom_server_btn.clicked.connect(self._choose_custom_server)
        self.stop_runtime_btn = QPushButton("Arresta server")
        self.stop_runtime_btn.setObjectName("pinkButton")
        self.stop_runtime_btn.setToolTip("Arresta il server gestito dall'app e forza la chiusura di eventuali llama-server.exe rimasti attivi")
        self.stop_runtime_btn.clicked.connect(self._force_stop_runtime)
        runtime_layout.addWidget(self.install_runtime_btn)
        runtime_layout.addWidget(self.custom_server_btn)
        runtime_layout.addWidget(self.stop_runtime_btn)
        self.runtime_label = QLabel("Runtime: non verificato")
        self.runtime_label.setObjectName("muted")
        self.runtime_label.setWordWrap(True)
        runtime_layout.addWidget(self.runtime_label)
        layout.addWidget(runtime_group)

        model_group = QGroupBox("Modello")
        model_layout = QVBoxLayout(model_group)
        model_layout.setSpacing(6)
        self.model_combo = QComboBox()
        self.model_combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.model_combo.setMinimumContentsLength(8)
        self.model_combo.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.model_combo.currentIndexChanged.connect(self._model_changed)
        model_layout.addWidget(self.model_combo)
        self.download_model_btn = QPushButton("Scarica")
        self.download_model_btn.clicked.connect(self._download_selected_model)
        self.import_model_btn = QPushButton("Importa GGUF")
        self.import_model_btn.clicked.connect(self._import_custom_model)
        model_layout.addWidget(self.download_model_btn)
        model_layout.addWidget(self.import_model_btn)
        layout.addWidget(model_group)

        web_group = QGroupBox("Web / RAG")
        web_layout = QVBoxLayout(web_group)
        web_layout.setSpacing(6)
        self.web_check = QCheckBox("Web")
        self.web_check.stateChanged.connect(self._save_settings_from_controls)
        self.web_engine_combo = QComboBox()
        self.web_engine_combo.addItem("DuckDuckGo", "direct")
        self.web_engine_combo.addItem("Brave", "brave")
        self.web_engine_combo.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.web_engine_combo.currentIndexChanged.connect(self._save_settings_from_controls)
        self.rag_check = QCheckBox("RAG locale")
        self.rag_check.stateChanged.connect(self._save_settings_from_controls)
        web_layout.addWidget(self.web_check)
        web_layout.addWidget(self.web_engine_combo)
        web_layout.addWidget(self.rag_check)

        docs_row = QHBoxLayout()
        docs_row.setSpacing(4)
        add_docs = QPushButton("+ File")
        add_docs.setToolTip("Aggiungi documenti al RAG")
        add_docs.clicked.connect(self._add_documents)
        add_folder = QPushButton("Cartella")
        add_folder.setToolTip("Indicizza una cartella e ricordala per gli aggiornamenti automatici")
        add_folder.clicked.connect(self._add_rag_folder)
        clear_docs = QPushButton("−")
        clear_docs.setToolTip("Svuota indice RAG")
        clear_docs.setObjectName("pinkButton")
        clear_docs.clicked.connect(self._clear_documents)
        docs_row.addWidget(add_docs)
        docs_row.addWidget(add_folder)
        docs_row.addWidget(clear_docs)
        web_layout.addLayout(docs_row)
        self.rag_pro_btn = QPushButton("RAG Pro · embeddings")
        self.rag_pro_btn.setToolTip("Scarica BGE-M3 e crea embeddings locali per ricerca ibrida BM25 + semantica")
        self.rag_pro_btn.clicked.connect(self._setup_rag_pro)
        web_layout.addWidget(self.rag_pro_btn)
        self.rag_label = QLabel("0 documenti")
        self.rag_label.setObjectName("muted")
        self.rag_label.setWordWrap(True)
        web_layout.addWidget(self.rag_label)
        layout.addWidget(web_group)

        advanced = QPushButton("⚙ Avanzate")
        advanced.clicked.connect(self._show_advanced_settings)
        layout.addWidget(advanced)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.hide()
        layout.addWidget(self.progress)

        open_data = QPushButton("Cartella dati")
        open_data.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(app_data_dir()))))
        layout.addWidget(open_data)
        layout.addStretch(1)

        scroll.setWidget(frame)
        return scroll

    def _build_chat_panel(self) -> QWidget:
        frame = QFrame()
        frame.setObjectName("chatPanel")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        top = QHBoxLayout()
        label = QLabel("CHAT LOCALE")
        label.setObjectName("subtitle")
        top.addWidget(label)
        top.addStretch(1)
        clear = QPushButton("Pulisci chat")
        clear.setObjectName("pinkButton")
        clear.clicked.connect(self._clear_chat)
        top.addWidget(clear)
        layout.addLayout(top)

        self.chat_scroll = QScrollArea()
        self.chat_scroll.setWidgetResizable(True)
        self.chat_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.chat_host = QWidget()
        self.chat_layout = QVBoxLayout(self.chat_host)
        self.chat_layout.setContentsMargins(6, 6, 6, 6)
        self.chat_layout.setSpacing(8)
        self.chat_layout.addStretch(1)
        self.chat_scroll.setWidget(self.chat_host)
        layout.addWidget(self.chat_scroll, 1)

        input_row = QHBoxLayout()
        self.prompt_edit = PromptEdit()
        self.prompt_edit.setPlaceholderText("Scrivi una domanda…  ·  Invio = invia  ·  Shift+Invio = nuova riga")
        self.prompt_edit.setMaximumHeight(130)
        self.prompt_edit.setMinimumHeight(76)
        self.prompt_edit.send_requested.connect(self._send)
        input_row.addWidget(self.prompt_edit, 1)
        send = QPushButton("INVIA")
        send.setMinimumWidth(112)
        send.setMinimumHeight(54)
        send.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        send.clicked.connect(self._send)
        self.send_btn = send
        input_row.addWidget(send)
        layout.addLayout(input_row)
        return frame

    @staticmethod
    def _spin(minimum: int, maximum: int, value: int, step: int) -> QSpinBox:
        spin = QSpinBox()
        spin.setRange(minimum, maximum)
        spin.setSingleStep(step)
        spin.setValue(value)
        return spin

    @staticmethod
    def _labeled(label: str, widget: QWidget) -> QHBoxLayout:
        row = QHBoxLayout()
        text = QLabel(label)
        text.setObjectName("muted")
        row.addWidget(text)
        row.addStretch(1)
        row.addWidget(widget)
        return row

    def _show_advanced_settings(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("Impostazioni avanzate")
        dialog.setMinimumWidth(430)
        form = QFormLayout(dialog)

        context = self._spin(512, 32768, self.settings.context_size, 512)
        tokens = self._spin(64, 4096, self.settings.max_tokens, 64)
        gpu = self._spin(0, 999, self.settings.gpu_layers, 1)
        threads = self._spin(1, 128, self.settings.threads, 1)
        port = self._spin(1024, 65535, self.settings.port, 1)
        brave = QLineEdit()
        brave.setPlaceholderText("Brave API key (opzionale)")
        brave.setEchoMode(QLineEdit.EchoMode.Password)
        brave.setText(self.secret_store.load_brave_key())

        form.addRow("Context", context)
        form.addRow("Max token", tokens)
        form.addRow("GPU layers", gpu)
        form.addRow("Thread CPU", threads)
        form.addRow("Porta server", port)
        form.addRow("Brave API key", brave)

        watched_box = QWidget()
        watched_layout = QVBoxLayout(watched_box)
        watched_layout.setContentsMargins(0, 0, 0, 0)
        watched_label = QLabel(
            "\n".join(self.settings.watched_folders) if self.settings.watched_folders else "Nessuna"
        )
        watched_label.setWordWrap(True)
        watched_label.setObjectName("muted")
        clear_watched = QPushButton("Dimentica cartelle")
        clear_watched.setObjectName("pinkButton")
        clear_watched.clicked.connect(lambda: (self.settings.watched_folders.clear(), watched_label.setText("Nessuna")))
        watched_layout.addWidget(watched_label)
        watched_layout.addWidget(clear_watched)
        form.addRow("Cartelle RAG", watched_box)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        form.addRow(buttons)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.settings.context_size = context.value()
            self.settings.max_tokens = tokens.value()
            self.settings.gpu_layers = gpu.value()
            self.settings.threads = threads.value()
            self.settings.port = port.value()
            self.context_spin.setValue(context.value())
            self.tokens_spin.setValue(tokens.value())
            self.gpu_spin.setValue(gpu.value())
            self.threads_spin.setValue(threads.value())
            self.brave_key_edit.setText(brave.text())
            self.secret_store.save_brave_key(brave.text())
            self.settings_store.save(self.settings)
            self._refresh_runtime_status()

    def _sync_controls_from_settings(self) -> None:
        self._select_data(self.backend_combo, self.settings.backend)
        self._select_data(self.web_engine_combo, self.settings.web_engine)
        self.context_spin.setValue(self.settings.context_size)
        self.tokens_spin.setValue(self.settings.max_tokens)
        self.gpu_spin.setValue(self.settings.gpu_layers)
        self.threads_spin.setValue(self.settings.threads)
        self.web_check.setChecked(self.settings.web_enabled)
        self.rag_check.setChecked(self.settings.rag_enabled)

    @staticmethod
    def _select_data(combo: QComboBox, value: str) -> None:
        for i in range(combo.count()):
            if combo.itemData(i) == value:
                combo.setCurrentIndex(i)
                return

    def _refresh_models(self) -> None:
        self.model_combo.blockSignals(True)
        self.model_combo.clear()
        target_index = 0
        for idx, preset in enumerate(CATALOG):
            state = "✓" if preset.path.is_file() else "↓"
            short_label = "Gemma 4 E2B" if preset.id == "gemma4-e2b" else "Qwen3 0.6B"
            self.model_combo.addItem(f"{state} {short_label} · {preset.approx_gb:.2f}G", ("preset", preset.id))
            self.model_combo.setItemData(self.model_combo.count() - 1, preset.label, Qt.ItemDataRole.ToolTipRole)
            if self.settings.active_model_id == preset.id:
                target_index = idx
        if self.settings.custom_model and Path(self.settings.custom_model).is_file():
            idx = self.model_combo.count()
            path = Path(self.settings.custom_model)
            self.model_combo.addItem(f"✓ Custom · {path.stem[:14]}", ("custom", str(path)))
            self.model_combo.setItemData(self.model_combo.count() - 1, str(path), Qt.ItemDataRole.ToolTipRole)
            if self.settings.active_model_id == "custom":
                target_index = idx
        self.model_combo.setCurrentIndex(target_index)
        self.model_combo.blockSignals(False)

    def _model_changed(self) -> None:
        data = self.model_combo.currentData()
        if not data:
            return
        kind, value = data
        if kind == "preset":
            preset = preset_by_id(value)
            if preset:
                self.settings.active_model_id = preset.id
                self.settings.context_size = preset.context
                self.settings.max_tokens = preset.max_tokens
                self.context_spin.setValue(preset.context)
                self.tokens_spin.setValue(preset.max_tokens)
        else:
            self.settings.active_model_id = "custom"
            self.settings.custom_model = value
        self.settings_store.save(self.settings)

    def _save_settings_from_controls(self) -> None:
        if not hasattr(self, "backend_combo"):
            return
        self.settings.backend = str(self.backend_combo.currentData() or "vulkan")
        self.settings.context_size = self.context_spin.value()
        self.settings.max_tokens = self.tokens_spin.value()
        self.settings.gpu_layers = self.gpu_spin.value()
        self.settings.threads = self.threads_spin.value()
        self.settings.web_enabled = self.web_check.isChecked()
        self.settings.web_engine = str(self.web_engine_combo.currentData() or "direct")
        self.settings.rag_enabled = self.rag_check.isChecked()
        self.settings_store.save(self.settings)
        self._refresh_runtime_status()

    def _runtime_path(self) -> Path:
        backend = self.settings.backend
        if backend == "custom":
            return Path(self.settings.custom_server) if self.settings.custom_server else Path()
        return RuntimeInstaller.installed_server(backend)

    def _model_path(self) -> Path:
        if self.settings.active_model_id == "custom":
            return Path(self.settings.custom_model) if self.settings.custom_model else Path()
        preset = preset_by_id(self.settings.active_model_id)
        return preset.path if preset else Path()

    def _engine_config(self) -> EngineConfig:
        return EngineConfig(
            server_exe=self._runtime_path(),
            model=self._model_path(),
            backend=self.settings.backend,
            context_size=self.settings.context_size,
            max_tokens=self.settings.max_tokens,
            gpu_layers=self.settings.gpu_layers,
            threads=self.settings.threads,
            port=self.settings.port,
        )

    def _install_runtime(self) -> None:
        backend = str(self.backend_combo.currentData() or "vulkan")
        if backend == "custom":
            self._choose_custom_server()
            return

        # Windows keeps llama.cpp DLLs locked while llama-server.exe is running.
        # Stop our local server before replacing/updating the runtime.
        self._set_status("Arresto llama-server prima dell'aggiornamento runtime…")
        self.server.stop()

        self._set_busy(True)
        self.progress.show()
        self.progress.setValue(0)
        worker = RuntimeInstallThread(backend)
        self.worker = worker
        worker.status.connect(self._set_status)
        worker.progress.connect(self.progress.setValue)
        worker.completed.connect(self._runtime_installed)
        worker.failed.connect(self._operation_failed)
        worker.finished.connect(lambda: self._set_busy(False))
        worker.start()

    def _force_stop_runtime(self) -> None:
        message = self.server.force_stop_all_windows()
        self._set_status(message)
        self._refresh_runtime_status()

    def _toggle_sidebar(self) -> None:
        if self.sidebar_scroll.isVisible():
            sizes = self.splitter.sizes()
            if sizes and sizes[0] > 0:
                self.settings.sidebar_width = max(195, min(225, sizes[0]))
            self.sidebar_scroll.hide()
            self.settings.sidebar_collapsed = True
            self.sidebar_toggle_btn.setText("☰ Mostra controlli")
        else:
            self.sidebar_scroll.show()
            width = max(195, min(225, int(self.settings.sidebar_width or 210)))
            total = max(width + 600, self.splitter.width())
            self.splitter.setSizes([width, max(600, total - width)])
            self.settings.sidebar_collapsed = False
            self.sidebar_toggle_btn.setText("◀ Nascondi controlli")
        self.settings_store.save(self.settings)

    def _splitter_moved(self, _pos: int, _index: int) -> None:
        if not self.sidebar_scroll.isVisible():
            return
        sizes = self.splitter.sizes()
        if sizes and sizes[0] > 0:
            self.settings.sidebar_width = max(195, min(225, sizes[0]))
            self.settings_store.save(self.settings)

    def _runtime_installed(self, path: str) -> None:
        self.progress.hide()
        self._set_status(f"Runtime installato: {path}")
        self._refresh_runtime_status()

    def _choose_custom_server(self) -> None:
        file_name, _ = QFileDialog.getOpenFileName(self, "Seleziona llama-server.exe", "", "llama-server.exe (llama-server.exe);;EXE (*.exe)")
        if file_name:
            self.settings.backend = "custom"
            self.settings.custom_server = file_name
            self._select_data(self.backend_combo, "custom")
            self.settings_store.save(self.settings)
            self._refresh_runtime_status()

    def _refresh_runtime_status(self) -> None:
        if not hasattr(self, "runtime_label"):
            return
        backend = self.settings.backend
        path = self._runtime_path()
        if path and path.is_file():
            self.runtime_label.setText(f"{backend.upper()} · pronto")
            self.runtime_label.setToolTip(str(path))
        else:
            self.runtime_label.setText(f"{backend.upper()} · non installato")
            self.runtime_label.setToolTip(str(path) if path else "")

    def _download_selected_model(self) -> None:
        data = self.model_combo.currentData()
        if not data or data[0] != "preset":
            QMessageBox.information(self, "Modello custom", "Il modello selezionato è già un file locale.")
            return
        preset = preset_by_id(data[1])
        if not preset:
            return
        if preset.path.is_file():
            self._set_status(f"Modello già presente: {preset.path.name}")
            return
        answer = QMessageBox.question(
            self,
            "Scarica modello",
            f"Scaricare {preset.label}?\n\nDimensione approssimativa: {preset.approx_gb:.2f} GB",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self._set_busy(True)
        self.progress.show()
        self.progress.setValue(0)
        worker = ModelDownloadThread(preset)
        self.worker = worker
        worker.status.connect(self._set_status)
        worker.progress.connect(self.progress.setValue)
        worker.completed.connect(lambda _path: self._model_downloaded(preset))
        worker.failed.connect(self._operation_failed)
        worker.finished.connect(lambda: self._set_busy(False))
        worker.start()

    def _model_downloaded(self, preset: ModelPreset) -> None:
        self.progress.hide()
        self.settings.active_model_id = preset.id
        self.settings.context_size = preset.context
        self.settings.max_tokens = preset.max_tokens
        self.settings_store.save(self.settings)
        self._refresh_models()
        self.context_spin.setValue(preset.context)
        self.tokens_spin.setValue(preset.max_tokens)
        self._set_status(f"Modello pronto: {preset.label}")

    def _import_custom_model(self) -> None:
        file_name, _ = QFileDialog.getOpenFileName(self, "Importa modello GGUF", "", "GGUF (*.gguf);;Tutti i file (*.*)")
        if not file_name:
            return
        self.settings.active_model_id = "custom"
        self.settings.custom_model = file_name
        self.settings_store.save(self.settings)
        self._refresh_models()
        self._set_status(f"Modello custom selezionato: {Path(file_name).name}")

    def _add_documents(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Aggiungi documenti al RAG",
            "",
            "Documenti (*.pdf *.txt *.md *.markdown *.html *.htm *.log *.csv);;Tutti i file (*.*)",
        )
        if not files:
            return
        self._set_busy(True)
        worker = RagBatchImportThread(self.rag, [Path(f) for f in files], self._engine_config())
        self.worker = worker
        worker.status.connect(self._set_status)
        worker.completed.connect(self._documents_batch_imported)
        worker.failed.connect(self._operation_failed)
        worker.finished.connect(lambda: self._set_busy(False))
        worker.start()

    def _documents_batch_imported(self, files: int, chunks: int) -> None:
        self.rag_check.setChecked(True)
        self._refresh_rag_status()
        self._set_status(f"RAG: {files} file indicizzati · {chunks} blocchi")

    def _add_rag_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Scegli cartella RAG")
        if not folder:
            return
        resolved = str(Path(folder).resolve())
        if resolved not in self.settings.watched_folders:
            self.settings.watched_folders.append(resolved)
            self.settings_store.save(self.settings)
        self._folder_sync_queue = [Path(resolved)]
        self._sync_next_folder()

    def _sync_watched_folders(self) -> None:
        if self.worker is not None:
            return
        folders = [Path(p) for p in self.settings.watched_folders if Path(p).is_dir()]
        if not folders:
            return
        self._folder_sync_queue = folders
        self._sync_next_folder()

    def _sync_next_folder(self) -> None:
        if self.worker is not None:
            return
        queue = getattr(self, "_folder_sync_queue", [])
        if not queue:
            self._refresh_rag_status()
            self._set_busy(False)
            return
        folder = queue.pop(0)
        self._set_busy(True)
        worker = RagFolderSyncThread(self.rag, folder, self._engine_config())
        self.worker = worker
        worker.status.connect(self._set_status)
        worker.completed.connect(self._folder_synced)
        worker.failed.connect(self._folder_sync_failed)
        worker.finished.connect(self._folder_sync_finished)
        worker.start()

    def _folder_synced(self, folder: str, changed: int, deleted: int, chunks: int) -> None:
        self.rag_check.setChecked(True)
        self._refresh_rag_status()
        if changed or deleted:
            self._set_status(f"Cartella RAG aggiornata: {changed} modificati · {deleted} rimossi · {chunks} blocchi")

    def _folder_sync_failed(self, message: str) -> None:
        self._set_status(f"Sync RAG: {message}")

    def _folder_sync_finished(self) -> None:
        self.worker = None
        QTimer.singleShot(50, self._sync_next_folder)

    def _setup_rag_pro(self) -> None:
        if embedding_model_installed():
            if not self.rag.chunks:
                QMessageBox.information(self, "RAG Pro", "BGE-M3 è già installato. Importa documenti per usare la ricerca ibrida.")
                return
            self._reembed_rag()
            return
        answer = QMessageBox.question(
            self,
            "RAG Pro",
            f"Scaricare BGE-M3 Q4_K_M (~{EMBEDDING_MODEL_APPROX_MB} MB)?\n\n"
            "Verrà usato solo in locale per embeddings semantici e reranking ibrido.",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self._set_busy(True)
        self.progress.show()
        self.progress.setValue(0)
        worker = EmbeddingModelDownloadThread()
        self.worker = worker
        worker.status.connect(self._set_status)
        worker.progress.connect(self.progress.setValue)
        worker.completed.connect(lambda _path: self._embedding_model_ready())
        worker.failed.connect(self._operation_failed)
        worker.finished.connect(lambda: self._set_busy(False))
        worker.start()

    def _embedding_model_ready(self) -> None:
        self.progress.hide()
        self._refresh_rag_status()
        self._set_status("BGE-M3 installato · RAG Pro pronto")
        if self.rag.chunks:
            QTimer.singleShot(100, self._reembed_rag)

    def _reembed_rag(self) -> None:
        if self.worker is not None:
            return
        config = self._engine_config()
        if not config.server_exe.is_file():
            QMessageBox.warning(self, "RAG Pro", "Installa prima il runtime llama.cpp CPU/Vulkan.")
            return
        self._set_busy(True)
        worker = RagReembedThread(self.rag, config)
        self.worker = worker
        worker.status.connect(self._set_status)
        worker.completed.connect(self._rag_reembedded)
        worker.failed.connect(self._operation_failed)
        worker.finished.connect(lambda: self._set_busy(False))
        worker.start()

    def _rag_reembedded(self, count: int) -> None:
        self._refresh_rag_status()
        self._set_status(f"RAG Pro: {count} blocchi con embeddings locali")

    def _clear_documents(self) -> None:
        if QMessageBox.question(self, "Svuota RAG", "Eliminare l'indice dei documenti locali?") == QMessageBox.StandardButton.Yes:
            self.rag.clear()
            self._refresh_rag_status()

    def _refresh_rag_status(self) -> None:
        if hasattr(self, "rag_label"):
            names = self.rag.document_names()
            embedded, total = self.rag.embedding_coverage()
            mode = "Hybrid" if embedding_model_installed() and embedded > 0 else "BM25"
            folders = len(self.settings.watched_folders)
            suffix = f" · {mode}" + (f" · {folders} cart." if folders else "")
            self.rag_label.setText(f"{len(names)} doc · {embedded}/{total} emb{suffix}")
            if hasattr(self, "rag_pro_btn"):
                self.rag_pro_btn.setText("RAG Pro · aggiorna" if embedding_model_installed() else "RAG Pro · installa")

    def _load_chat_ui(self) -> None:
        if not self.history:
            self._add_bubble(
                "ELintelligence",
                "Pronto. Installa llama.cpp, scarica o importa un GGUF e poi scrivimi. La generazione resta sul PC.",
                True,
                [],
            )
            return
        for item in self.history:
            self._add_bubble(
                "ELintelligence" if item.role == "assistant" else "Tu",
                item.text,
                item.role == "assistant",
                item.sources or [],
            )

    def _add_bubble(self, title: str, text: str, assistant: bool, sources: list[dict] | None = None) -> ChatBubble:
        bubble = ChatBubble(title, text, assistant, sources)
        wrapper = QWidget()
        row = QHBoxLayout(wrapper)
        row.setContentsMargins(2, 1, 2, 1)
        if assistant:
            row.addWidget(bubble, 1)
            row.addStretch(0)
        else:
            row.addStretch(1)
            row.addWidget(bubble, 1)
        self.chat_layout.insertWidget(self.chat_layout.count() - 1, wrapper)
        self._scroll_bottom()
        return bubble

    def _send(self) -> None:
        if self.worker is not None and self.worker.isRunning():
            return
        question = self.prompt_edit.toPlainText().strip()
        if not question:
            return
        config = self._engine_config()
        if not config.server_exe.is_file():
            QMessageBox.warning(self, "Runtime mancante", "Installa llama.cpp CPU/Vulkan oppure scegli un llama-server.exe personalizzato.")
            return
        if not config.model.is_file():
            QMessageBox.warning(self, "Modello mancante", "Scarica o importa prima un modello GGUF.")
            return

        self.prompt_edit.clear()
        self._add_bubble("Tu", question, False, [])
        previous = list(self.history)
        self.history.append(ChatMessage(role="user", text=question, sources=[]))
        self.chat_store.save(self.history)

        self.current_answer = ""
        self.current_assistant_bubble = self._add_bubble("ELintelligence", "", True, [])
        self._set_busy(True)

        worker = ChatThread(
            server=self.server,
            config=config,
            history=previous,
            question=question,
            web_enabled=self.web_check.isChecked(),
            web_engine=str(self.web_engine_combo.currentData() or "direct"),
            brave_key=self.brave_key_edit.text(),
            rag_enabled=self.rag_check.isChecked(),
            rag=self.rag,
        )
        self.worker = worker
        worker.status.connect(self._set_status)
        worker.token.connect(self._chat_token)
        worker.sources_ready.connect(self._chat_sources)
        worker.completed.connect(self._chat_completed)
        worker.failed.connect(self._chat_failed)
        worker.finished.connect(lambda: self._set_busy(False))
        worker.start()

    def _chat_token(self, token: str) -> None:
        self.current_answer += token
        if self.current_assistant_bubble:
            self.current_assistant_bubble.set_text(self.current_answer)
        self._scroll_bottom()

    def _chat_sources(self, sources: list[dict]) -> None:
        if self.current_assistant_bubble:
            self.current_assistant_bubble.set_sources(sources)

    def _chat_completed(self, answer: str, sources: list[dict]) -> None:
        if self.current_assistant_bubble:
            self.current_assistant_bubble.set_text(answer)
            self.current_assistant_bubble.set_sources(sources)
        self.history.append(ChatMessage(role="assistant", text=answer, sources=sources))
        self.chat_store.save(self.history)
        self._set_status("Pronto")
        self.current_assistant_bubble = None
        self.current_answer = ""

    def _chat_failed(self, message: str) -> None:
        text = f"Errore: {message}"
        if self.current_assistant_bubble:
            self.current_assistant_bubble.set_text(text)
        self._set_status(text)
        self.current_assistant_bubble = None
        self.current_answer = ""

    def _clear_chat(self) -> None:
        if QMessageBox.question(self, "Pulisci chat", "Cancellare la cronologia locale della chat?") != QMessageBox.StandardButton.Yes:
            return
        self.history.clear()
        self.chat_store.clear()
        while self.chat_layout.count() > 1:
            item = self.chat_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        self._add_bubble("ELintelligence", "Cronologia cancellata. Nuova chat pronta.", True, [])

    def _operation_failed(self, message: str) -> None:
        self.progress.hide()
        self._set_status(f"Errore: {message}")
        QMessageBox.critical(self, "ELintelligence", message)

    def _set_busy(self, busy: bool) -> None:
        self.send_btn.setEnabled(not busy)
        self.install_runtime_btn.setEnabled(not busy)
        self.download_model_btn.setEnabled(not busy)
        self.import_model_btn.setEnabled(not busy)
        if hasattr(self, "rag_pro_btn"):
            self.rag_pro_btn.setEnabled(not busy)
        if not busy:
            if self.progress.value() >= 100:
                self.progress.hide()
            self.worker = None

    def _set_status(self, text: str) -> None:
        self.status_label.setText(text)

    def _scroll_bottom(self) -> None:
        QTimer.singleShot(0, lambda: self.chat_scroll.verticalScrollBar().setValue(self.chat_scroll.verticalScrollBar().maximum()))

    def closeEvent(self, event: QCloseEvent) -> None:
        if hasattr(self, "splitter") and hasattr(self, "sidebar_scroll") and self.sidebar_scroll.isVisible():
            sizes = self.splitter.sizes()
            if sizes and sizes[0] > 0:
                self.settings.sidebar_width = max(195, min(225, sizes[0]))
        self.secret_store.save_brave_key(self.brave_key_edit.text())
        self._save_settings_from_controls()
        self.settings_store.save(self.settings)
        self.server.stop()
        event.accept()


def run() -> int:
    app = QApplication.instance() or QApplication([])
    app.setApplicationName("ELintelligence")
    app.setOrganizationName("ELintelligence")
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    return app.exec()
