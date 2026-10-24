"""
Settings & Configuration View
Handles Visual Themes & Appearance, Company Profile, 1-Click SQLite Backups,
Restore, Sample Data, and Hardware-Locked Offline Licensing.
"""
from pathlib import Path
import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QTabWidget, QFrame,
    QFormLayout, QFileDialog, QApplication, QRadioButton, QButtonGroup,
    QScrollArea, QCheckBox, QDoubleSpinBox
)
from decimal import Decimal
from PySide6.QtCore import Qt, Signal, QSettings
from PySide6.QtGui import QFont

from app.database.connection import get_session, create_backup, restore_backup
from app.database.models import CompanyProfile
from app.services.license_service import get_license_status, activate_license, get_machine_fingerprint
from app.services.sample_data import populate_sample_data, clear_all_business_data
from app.config import INDIAN_STATES, DB_PATH, BACKUP_DIR
from app.core.diagnostics import run_system_health_check, dump_thread_stacks, get_memory_usage_mb
from app.core.logger import LOG_DIR
from app.ui.theme import (
    theme_manager, PageHeaderWidget, CardFrame, StatusBadgeLabel,
    ThemedMessageBox
)
from app.ui.async_worker import run_in_background


class SettingsView(QWidget):
    profile_updated = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_logo_path = None
        self.current_seal_path = None
        self.current_sig_path = None
        self.init_ui()
        # Connect to theme changes to refresh dynamic preview
        theme_manager.theme_changed.connect(self.on_theme_changed)

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        header = PageHeaderWidget(
            title="Settings & Preferences",
            subtitle="Configure appearance themes, company profile, database backups, and system licensing"
        )
        layout.addWidget(header)

        self.tabs = QTabWidget()

        # Tab 1: Company Profile, Appearance Theme & PDF Document Suite
        self.tab_company = QWidget()
        self.tab_pdf_suite = QWidget()
        self.init_pdf_suite_tab()
        QApplication.processEvents()
        self.init_company_and_theme_tab()
        QApplication.processEvents()
        self.tabs.addTab(self.tab_company, "🏢 Company Profile & Print Settings")

        # Tab 2: Database & Backup
        self.tab_backup = QWidget()
        self.init_backup_tab()
        QApplication.processEvents()
        self.tabs.addTab(self.tab_backup, "💾 Backup & Database Management")

        # Tab 3: Offline Licensing
        self.tab_license = QWidget()
        self.init_license_tab()
        QApplication.processEvents()
        self.tabs.addTab(self.tab_license, "🔑 Offline License & Activation")

        # Tab 4: System Diagnostics & Crash Logs
        self.tab_diagnostics = QWidget()
        self.init_diagnostics_tab()
        QApplication.processEvents()
        self.tabs.addTab(self.tab_diagnostics, "🩺 System Health & Crash Diagnostics")

        layout.addWidget(self.tabs, 1)

    # ========================================================
    # Tab 1: Company Profile + Central Theme Switcher & Preview
    # ========================================================
    def init_company_and_theme_tab(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        content = QWidget()
        main_h = QHBoxLayout(content)
        main_h.setContentsMargins(12, 12, 12, 12)
        main_h.setSpacing(16)

        # ----------------- Left Column: Company Profile Form -----------------
        left_col = QVBoxLayout()
        left_col.setSpacing(12)

        card_comp = CardFrame()
        card_layout = QVBoxLayout(card_comp)
        card_layout.setSpacing(12)

        lbl_ct = QLabel("Company Information & Bank Details")
        lbl_ct.setProperty("variant", "title")
        lbl_ct.setFont(theme_manager.font("subtitle"))
        card_layout.addWidget(lbl_ct)

        form_layout = QFormLayout()
        form_layout.setSpacing(8)

        self.inp_cname = QLineEdit()
        form_layout.addRow("Company Name *:", self.inp_cname)

        from app.ui.widgets.upper_line_edit import UpperLineEdit
        self.inp_cgstin = UpperLineEdit()
        form_layout.addRow("GSTIN:", self.inp_cgstin)

        self.inp_cpan = UpperLineEdit()
        form_layout.addRow("PAN:", self.inp_cpan)

        self.inp_cphone = QLineEdit()
        form_layout.addRow("Phone / Mobile:", self.inp_cphone)

        self.inp_cemail = QLineEdit()
        form_layout.addRow("Email:", self.inp_cemail)

        self.inp_caddr = QLineEdit()
        form_layout.addRow("Address:", self.inp_caddr)

        self.inp_ccity = QLineEdit()
        form_layout.addRow("City:", self.inp_ccity)

        self.combo_cstate = QComboBox()
        self.combo_cstate.addItem("-- Select State --", userData=("", ""))
        for code, st_name in INDIAN_STATES:
            self.combo_cstate.addItem(f"{code} - {st_name}", userData=(code, st_name))
        form_layout.addRow("State & Code:", self.combo_cstate)

        # Bank Details
        self.inp_bank_name = QLineEdit()
        form_layout.addRow("Bank Name:", self.inp_bank_name)

        self.inp_bank_ac = QLineEdit()
        form_layout.addRow("Bank A/C No:", self.inp_bank_ac)

        self.inp_bank_ifsc = UpperLineEdit()
        form_layout.addRow("Bank IFSC:", self.inp_bank_ifsc)

        self.inp_upi = QLineEdit()
        form_layout.addRow("UPI ID (Payments):", self.inp_upi)

        # Logo Picker Row
        logo_box = QHBoxLayout()
        self.lbl_logo_path = QLabel("No logo selected")
        self.lbl_logo_path.setProperty("variant", "caption")
        btn_browse_logo = QPushButton("Browse Logo...")
        btn_browse_logo.setProperty("variant", "secondary")
        btn_browse_logo.setIcon(theme_manager.icon("file_text", size=14))
        btn_browse_logo.clicked.connect(self.browse_logo)

        btn_clear_logo = QPushButton("Clear")
        btn_clear_logo.setProperty("variant", "ghost")
        btn_clear_logo.clicked.connect(
            lambda: [setattr(self, 'current_logo_path', None), self.lbl_logo_path.setText("No logo selected")]
        )
        logo_box.addWidget(btn_browse_logo)
        logo_box.addWidget(btn_clear_logo)
        logo_box.addWidget(self.lbl_logo_path, 1)
        form_layout.addRow("Company Logo:", logo_box)
        self.current_logo_path = None

        self.txt_terms = QTextEdit()
        self.txt_terms.setMaximumHeight(65)
        form_layout.addRow("Invoice Terms:", self.txt_terms)

        self.txt_whatsapp_template = QTextEdit()
        self.txt_whatsapp_template.setMaximumHeight(85)
        self.txt_whatsapp_template.setToolTip("Custom template for payment reminders. Placeholders: {party_name}, {company_name}, {amount}, {bank_details}")
        form_layout.addRow("WhatsApp Template:", self.txt_whatsapp_template)

        self.chk_negative_stock = QCheckBox("Allow negative stock (allow billing when inventory is insufficient)")
        self.chk_negative_stock.setToolTip("When enabled, stock may go negative honestly and is never clamped to zero.")
        form_layout.addRow("Inventory Policy:", self.chk_negative_stock)

        card_layout.addLayout(form_layout)
        left_col.addWidget(card_comp)

        btn_save = QPushButton("Save Company Profile")
        btn_save.setProperty("variant", "primary")
        btn_save.setIcon(theme_manager.icon("check", color_token="text_on_accent", size=16))
        btn_save.clicked.connect(self.save_company_profile)
        left_col.addWidget(btn_save, alignment=Qt.AlignRight)

        main_h.addLayout(left_col, 5)
        QApplication.processEvents()

        # ----------------- Right Column: Appearance & Live Preview -----------------
        right_col = QVBoxLayout()
        right_col.setSpacing(12)

        # Theme Selector Card
        sel_card = CardFrame()
        sel_layout = QVBoxLayout(sel_card)
        sel_layout.setSpacing(10)

        lbl_t = QLabel("Visual Theme & Palette")
        lbl_t.setProperty("variant", "title")
        lbl_t.setFont(theme_manager.font("subtitle"))
        sel_layout.addWidget(lbl_t)

        lbl_desc = QLabel("Switch between high-contrast enterprise themes with zero restart:")
        lbl_desc.setProperty("variant", "subtitle")
        lbl_desc.setWordWrap(True)
        sel_layout.addWidget(lbl_desc)

        self.theme_group = QButtonGroup(self)

        self.rb_light = QRadioButton("☀️ Professional Light (Default Enterprise)")
        self.rb_dark = QRadioButton("🌙 Professional Dark (High-Contrast Dark Surfaces)")
        self.rb_navy = QRadioButton("⚓ Classic Navy (Executive Navy Brand Palette)")
        self.rb_system = QRadioButton("💻 Follow System (Automatically match Windows OS)")
        self.rb_custom = QRadioButton("📁 Custom Theme (.json file)")

        for rb in (self.rb_light, self.rb_dark, self.rb_navy, self.rb_system, self.rb_custom):
            rb.setFont(theme_manager.font("body"))
            sel_layout.addWidget(rb)
            self.theme_group.addButton(rb)

        custom_row = QHBoxLayout()
        self.lbl_custom_path = QLabel("No custom theme loaded")
        self.lbl_custom_path.setProperty("variant", "caption")
        btn_browse_custom = QPushButton("Browse JSON...")
        btn_browse_custom.setProperty("variant", "secondary")
        btn_browse_custom.clicked.connect(self.handle_browse_custom_theme)
        custom_row.addWidget(btn_browse_custom)
        custom_row.addWidget(self.lbl_custom_path, 1)
        sel_layout.addLayout(custom_row)

        cur_mode = theme_manager.theme_mode
        if cur_mode == "professional_dark":
            self.rb_dark.setChecked(True)
        elif cur_mode == "classic_navy":
            self.rb_navy.setChecked(True)
        elif cur_mode == "system":
            self.rb_system.setChecked(True)
        elif cur_mode == "custom":
            self.rb_custom.setChecked(True)
        else:
            self.rb_light.setChecked(True)

        self.theme_group.buttonClicked.connect(self.on_theme_radio_changed)

        # Startup & Animation Preferences
        sel_layout.addSpacing(10)
        lbl_startup_opts = QLabel("Startup & Animation Options")
        lbl_startup_opts.setProperty("variant", "label")
        sel_layout.addWidget(lbl_startup_opts)

        qsettings = QSettings("BillFlow", "ThemeSystem")
        self.chk_show_splash = QCheckBox("Show opening screen (Animated Splash)")
        val_splash = qsettings.value("show_splash", True)
        self.chk_show_splash.setChecked(val_splash if isinstance(val_splash, bool) else str(val_splash).lower() in ("true", "1"))
        self.chk_show_splash.toggled.connect(lambda chk: qsettings.setValue("show_splash", chk))
        sel_layout.addWidget(self.chk_show_splash)

        self.chk_reduce_motion = QCheckBox("Reduce motion (disable animations and transitions)")
        val_motion = qsettings.value("reduce_motion", False)
        self.chk_reduce_motion.setChecked(val_motion if isinstance(val_motion, bool) else str(val_motion).lower() in ("true", "1"))
        self.chk_reduce_motion.toggled.connect(lambda chk: qsettings.setValue("reduce_motion", chk))
        sel_layout.addWidget(self.chk_reduce_motion)

        sel_layout.addSpacing(6)
        btn_about_app = QPushButton("About BillFlow Suite...")
        btn_about_app.setProperty("variant", "secondary")
        btn_about_app.setIcon(theme_manager.icon("info", size=16))
        btn_about_app.clicked.connect(self.open_about_dialog)
        sel_layout.addWidget(btn_about_app)

        right_col.addWidget(sel_card)

        # Live Interactive Preview Card
        self.preview_card = CardFrame()
        p_layout = QVBoxLayout(self.preview_card)
        p_layout.setSpacing(10)

        lbl_pt = QLabel("Live Theme Preview")
        lbl_pt.setProperty("variant", "title")
        lbl_pt.setFont(theme_manager.font("subtitle"))
        p_layout.addWidget(lbl_pt)

        self.demo_surface = CardFrame()
        ds_layout = QVBoxLayout(self.demo_surface)
        ds_layout.setSpacing(10)

        hdr_row = QHBoxLayout()
        lbl_demo_hdr = QLabel("Acme Traders Pvt Ltd")
        lbl_demo_hdr.setFont(theme_manager.font("subtitle"))
        hdr_row.addWidget(lbl_demo_hdr)
        hdr_row.addStretch()
        self.lbl_demo_amount = QLabel("₹ 1,24,500.00")
        self.lbl_demo_amount.setFont(theme_manager.font("tabular"))
        self.lbl_demo_amount.setProperty("variant", "headline")
        hdr_row.addWidget(self.lbl_demo_amount)
        ds_layout.addLayout(hdr_row)

        badge_row = QHBoxLayout()
        badge_row.setSpacing(6)
        badge_row.addWidget(StatusBadgeLabel("PAID"))
        badge_row.addWidget(StatusBadgeLabel("PARTIAL"))
        badge_row.addWidget(StatusBadgeLabel("OVERDUE"))
        badge_row.addWidget(StatusBadgeLabel("DRAFT"))
        badge_row.addStretch()
        ds_layout.addLayout(badge_row)

        btn_bar = QHBoxLayout()
        btn_bar.setSpacing(6)
        p_btn = QPushButton("Primary")
        p_btn.setProperty("variant", "primary")
        s_btn = QPushButton("Secondary")
        s_btn.setProperty("variant", "secondary")
        d_btn = QPushButton("Danger")
        d_btn.setProperty("variant", "danger")
        g_btn = QPushButton("Ghost")
        g_btn.setProperty("variant", "ghost")
        btn_bar.addWidget(p_btn)
        btn_bar.addWidget(s_btn)
        btn_bar.addWidget(d_btn)
        btn_bar.addWidget(g_btn)
        ds_layout.addLayout(btn_bar)

        p_layout.addWidget(self.demo_surface)

        # WCAG note
        lbl_wcag = QLabel(
            "<b>Accessibility Guarantee:</b> All shipped themes are verified to meet "
            "<b>WCAG 2.1 AA Contrast standards</b> (minimum 4.5:1 text ratio)."
        )
        lbl_wcag.setWordWrap(True)
        lbl_wcag.setFont(theme_manager.font("caption"))
        p_layout.addWidget(lbl_wcag)

        right_col.addWidget(self.preview_card)
        right_col.addStretch()

        main_h.addLayout(right_col, 5)

        scroll.setWidget(content)

        self.company_subtabs = QTabWidget()
        self.company_subtabs.addTab(scroll, "🏢 Company & Visual Theme")
        self.company_subtabs.addTab(self.tab_pdf_suite, "📄 PDF Document Suite & Print Settings")

        outer_layout = QVBoxLayout(self.tab_company)
        outer_layout.setContentsMargins(4, 4, 4, 4)
        outer_layout.addWidget(self.company_subtabs)

        self.load_company_profile()

    def on_theme_radio_changed(self, button):
        if button == self.rb_light:
            theme_manager.apply_theme("professional_light")
        elif button == self.rb_dark:
            theme_manager.apply_theme("professional_dark")
        elif button == self.rb_navy:
            theme_manager.apply_theme("classic_navy")
        elif button == self.rb_system:
            theme_manager.apply_theme("system")

    def open_about_dialog(self):
        """Open the enterprise About & Diagnostics dialog."""
        from app.ui.about_dialog import AboutDialog
        dlg = AboutDialog(self)
        dlg.exec()


    def handle_browse_custom_theme(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Custom Theme JSON File",
            "", "Theme Files (*.json);;All Files (*.*)"
        )
        if file_path:
            self.lbl_custom_path.setText(Path(file_path).name)
            success = theme_manager.apply_theme(file_path)
            if success:
                self.rb_custom.setChecked(True)
                ThemedMessageBox.information(
                    self, "Theme Applied",
                    f"Successfully loaded and applied custom theme from:\n{Path(file_path).name}"
                )
            else:
                ThemedMessageBox.warning(
                    self, "Invalid Theme",
                    "Custom theme JSON has invalid tokens. Safely reverted to default."
                )

    def on_theme_changed(self, tokens):
        """Called whenever active theme switches; refreshes fonts & styles."""
        self.lbl_demo_amount.setFont(theme_manager.font("tabular"))

    def browse_logo(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Company Logo Image", "",
            "Image Files (*.png *.jpg *.jpeg);;All Files (*.*)"
        )
        if file_path:
            try:
                from app.services.validation_helpers import validate_and_store_logo
                saved_path = validate_and_store_logo(file_path)
                self.current_logo_path = saved_path
                self.lbl_logo_path.setText(Path(saved_path).name)
            except Exception as e:
                ThemedMessageBox.warning(self, "Invalid Logo", str(e))

    def load_company_profile(self):
        with get_session() as session:
            comp = session.query(CompanyProfile).first()
            if comp:
                self.inp_cname.setText(comp.name or "")
                self.inp_cgstin.setText(comp.gstin or "")
                self.inp_cpan.setText(comp.pan or "")
                self.inp_cphone.setText(comp.phone or "")
                self.inp_cemail.setText(comp.email or "")
                self.inp_caddr.setText(comp.address or "")
                self.inp_ccity.setText(comp.city or "")

                st_code = comp.state_code or ""
                matched = False
                for i in range(self.combo_cstate.count()):
                    data = self.combo_cstate.itemData(i)
                    if data and data[0] == st_code and st_code:
                        self.combo_cstate.setCurrentIndex(i)
                        matched = True
                        break
                if not matched:
                    self.combo_cstate.setCurrentIndex(0)

                self.inp_bank_name.setText(comp.bank_name or "")
                self.inp_bank_ac.setText(comp.bank_account_no or "")
                self.inp_bank_ifsc.setText(comp.bank_ifsc or "")
                self.inp_upi.setText(comp.upi_id or "")
                self.txt_terms.setPlainText(comp.terms_conditions or "")
                self.txt_whatsapp_template.setPlainText(getattr(comp, "whatsapp_template", None) or "Dear {party_name},\n\nGreetings from *{company_name}*!\n\nThis is a gentle reminder that your current outstanding balance is *₹{amount}*.\n\nKindly arrange for payment at your earliest convenience. If already paid, please ignore this message.\n\nWarm regards,\n*{company_name}*")
                self.chk_negative_stock.setChecked(getattr(comp, "allow_negative_stock", False) or False)

                if comp.logo_path and Path(comp.logo_path).exists():
                    self.current_logo_path = comp.logo_path
                    self.lbl_logo_path.setText(Path(comp.logo_path).name)
                else:
                    self.current_logo_path = None
                    self.lbl_logo_path.setText("No logo selected")

                self.load_pdf_suite_settings(comp)

    def save_company_profile(self):
        st_data = self.combo_cstate.currentData()
        st_code, st_name = st_data if st_data else ("", "")
        if not st_code:
            st_name = ""

        with get_session() as session:
            comp = session.query(CompanyProfile).first()
            if not comp:
                comp = CompanyProfile()
                session.add(comp)

            comp.name = self.inp_cname.text().strip()
            comp.gstin = self.inp_cgstin.text().strip().upper()
            comp.pan = self.inp_cpan.text().strip().upper()
            comp.phone = self.inp_cphone.text().strip()
            comp.email = self.inp_cemail.text().strip()
            comp.address = self.inp_caddr.text().strip()
            comp.city = self.inp_ccity.text().strip()
            comp.state = st_name or None
            comp.state_code = st_code or None
            comp.bank_name = self.inp_bank_name.text().strip()
            comp.bank_account_no = self.inp_bank_ac.text().strip()
            comp.bank_ifsc = self.inp_bank_ifsc.text().strip().upper()
            comp.upi_id = self.inp_upi.text().strip()
            comp.logo_path = self.current_logo_path
            comp.terms_conditions = self.txt_terms.toPlainText().strip()
            comp.whatsapp_template = self.txt_whatsapp_template.toPlainText().strip()
            comp.allow_negative_stock = self.chk_negative_stock.isChecked()
            session.commit()

        ThemedMessageBox.information(self, "Success", "Company profile saved successfully!")
        self.profile_updated.emit()

    def init_pdf_suite_tab(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # Card 1: Branding & Authorization Imagery
        card_img = CardFrame()
        c_layout1 = QVBoxLayout(card_img)
        c_layout1.setSpacing(12)

        lbl_t1 = QLabel("Branding & Authorization Imagery")
        lbl_t1.setFont(theme_manager.font("subtitle"))
        c_layout1.addWidget(lbl_t1)

        f_layout1 = QFormLayout()
        f_layout1.setSpacing(10)

        # Seal
        seal_row = QHBoxLayout()
        self.btn_seal = QPushButton("Choose Seal Image...")
        self.btn_seal.setProperty("variant", "secondary")
        self.btn_seal.clicked.connect(self.browse_seal)
        self.lbl_seal_path = QLabel("No seal selected")
        self.lbl_seal_path.setFont(theme_manager.font("caption"))
        btn_clear_seal = QPushButton("Remove")
        btn_clear_seal.setProperty("variant", "ghost")
        btn_clear_seal.clicked.connect(self.clear_seal)
        seal_row.addWidget(self.btn_seal)
        seal_row.addWidget(self.lbl_seal_path, 1)
        seal_row.addWidget(btn_clear_seal)
        f_layout1.addRow("Official Company Seal / Stamp:", seal_row)

        # Signature
        sig_row = QHBoxLayout()
        self.btn_sig = QPushButton("Choose Signature Image...")
        self.btn_sig.setProperty("variant", "secondary")
        self.btn_sig.clicked.connect(self.browse_signature)
        self.lbl_sig_path = QLabel("No signature selected")
        self.lbl_sig_path.setFont(theme_manager.font("caption"))
        btn_clear_sig = QPushButton("Remove")
        btn_clear_sig.setProperty("variant", "ghost")
        btn_clear_sig.clicked.connect(self.clear_signature)
        sig_row.addWidget(self.btn_sig)
        sig_row.addWidget(self.lbl_sig_path, 1)
        sig_row.addWidget(btn_clear_sig)
        f_layout1.addRow("Authorised Signatory Signature:", sig_row)

        c_layout1.addLayout(f_layout1)
        layout.addWidget(card_img)

        # Card 2: Print & Output Options
        card_opts = CardFrame()
        c_layout2 = QVBoxLayout(card_opts)
        c_layout2.setSpacing(12)

        lbl_t2 = QLabel("Document Output & Print Options")
        lbl_t2.setFont(theme_manager.font("subtitle"))
        c_layout2.addWidget(lbl_t2)

        f_layout2 = QFormLayout()
        f_layout2.setSpacing(10)

        self.combo_num_fmt = QComboBox()
        self.combo_num_fmt.addItem("Indian Numbering (₹ 1,23,456.78)", "Indian")
        self.combo_num_fmt.addItem("International Numbering (₹ 123,456.78)", "International")
        f_layout2.addRow("Currency & Number Format:", self.combo_num_fmt)

        self.chk_print_all_copies = QCheckBox("Print Triplicate Copies for Tax Invoices (Original, Duplicate, Triplicate)")
        f_layout2.addRow("", self.chk_print_all_copies)

        self.chk_print_hsn_summary = QCheckBox("Include HSN/SAC Tax Breakdown Summary on Invoices")
        f_layout2.addRow("", self.chk_print_hsn_summary)

        self.chk_show_value_on_challan = QCheckBox("Display Item Unit Prices & Totals on Delivery Challans")
        f_layout2.addRow("", self.chk_show_value_on_challan)

        self.chk_adaptive_font = QCheckBox("Auto-size item text to fill the page")
        self.chk_adaptive_font.toggled.connect(self._on_adaptive_font_toggled)
        f_layout2.addRow("", self.chk_adaptive_font)

        self.spn_font_max = QDoubleSpinBox()
        self.spn_font_max.setRange(6.0, 16.0)
        self.spn_font_max.setSingleStep(0.25)
        self.spn_font_max.setValue(13.0)
        self.spn_font_max.setSuffix(" pt")
        f_layout2.addRow("Largest item text size:", self.spn_font_max)

        self.spn_font_min = QDoubleSpinBox()
        self.spn_font_min.setRange(6.0, 16.0)
        self.spn_font_min.setSingleStep(0.25)
        self.spn_font_min.setValue(7.5)
        self.spn_font_min.setSuffix(" pt")
        f_layout2.addRow("Smallest item text size:", self.spn_font_min)

        # Export & Save Location Settings
        self.chk_ask_save = QCheckBox("Ask where to save every time when exporting (PDF / Excel)")
        self.chk_ask_save.setChecked(True)
        f_layout2.addRow("", self.chk_ask_save)

        folder_row = QHBoxLayout()
        self.inp_export_folder = QLineEdit()
        self.inp_export_folder.setPlaceholderText("Default export folder (optional)...")
        btn_browse_folder = QPushButton("Browse...")
        btn_browse_folder.setProperty("variant", "secondary")
        btn_browse_folder.clicked.connect(self._browse_default_export_folder)
        folder_row.addWidget(self.inp_export_folder, 1)
        folder_row.addWidget(btn_browse_folder)
        f_layout2.addRow("Default Export Folder:", folder_row)

        c_layout2.addLayout(f_layout2)
        layout.addWidget(card_opts)

        # Card 3: Statutory Declarations & Document Terms
        card_terms = CardFrame()
        c_layout3 = QVBoxLayout(card_terms)
        c_layout3.setSpacing(12)

        lbl_t3 = QLabel("Statutory Declarations & Per-Document Terms")
        lbl_t3.setFont(theme_manager.font("subtitle"))
        c_layout3.addWidget(lbl_t3)

        f_layout3 = QFormLayout()
        f_layout3.setSpacing(10)

        self.txt_declaration = QTextEdit()
        self.txt_declaration.setMaximumHeight(65)
        f_layout3.addRow("Tax Invoice Legal Declaration:", self.txt_declaration)

        self.txt_terms_quotation = QTextEdit()
        self.txt_terms_quotation.setMaximumHeight(65)
        f_layout3.addRow("Quotation Terms & Conditions:", self.txt_terms_quotation)

        self.txt_terms_po = QTextEdit()
        self.txt_terms_po.setMaximumHeight(65)
        f_layout3.addRow("Purchase Order Instructions:", self.txt_terms_po)

        self.txt_terms_proforma = QTextEdit()
        self.txt_terms_proforma.setMaximumHeight(65)
        f_layout3.addRow("Proforma Invoice Terms:", self.txt_terms_proforma)

        self.txt_notes_challan = QTextEdit()
        self.txt_notes_challan.setMaximumHeight(65)
        f_layout3.addRow("Delivery Challan Default Note:", self.txt_notes_challan)

        c_layout3.addLayout(f_layout3)
        layout.addWidget(card_terms)

        # Save Button
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_save = QPushButton("Save PDF Settings")
        btn_save.setProperty("variant", "primary")
        btn_save.setIcon(theme_manager.icon("check", color_token="text_on_accent", size=16))
        btn_save.clicked.connect(self.save_pdf_suite_settings)
        btn_row.addWidget(btn_save)
        layout.addLayout(btn_row)

        scroll.setWidget(content)
        outer = QVBoxLayout(self.tab_pdf_suite)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        with get_session() as session:
            comp = session.query(CompanyProfile).first()
            if comp:
                self.load_pdf_suite_settings(comp)

    def browse_seal(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Company Seal / Stamp Image", "",
            "Image Files (*.png *.jpg *.jpeg);;All Files (*.*)"
        )
        if file_path:
            try:
                from app.services.validation_helpers import validate_and_store_image
                saved_path = validate_and_store_image(file_path, "company_seal")
                self.current_seal_path = saved_path
                self.lbl_seal_path.setText(Path(saved_path).name)
            except Exception as e:
                ThemedMessageBox.warning(self, "Invalid Seal Image", str(e))

    def clear_seal(self):
        self.current_seal_path = None
        self.lbl_seal_path.setText("No seal selected")

    def browse_signature(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Authorised Signatory Signature Image", "",
            "Image Files (*.png *.jpg *.jpeg);;All Files (*.*)"
        )
        if file_path:
            try:
                from app.services.validation_helpers import validate_and_store_image
                saved_path = validate_and_store_image(file_path, "company_signature")
                self.current_sig_path = saved_path
                self.lbl_sig_path.setText(Path(saved_path).name)
            except Exception as e:
                ThemedMessageBox.warning(self, "Invalid Signature Image", str(e))

    def clear_signature(self):
        self.current_sig_path = None
        self.lbl_sig_path.setText("No signature selected")

    def load_pdf_suite_settings(self, comp):
        if not comp or not hasattr(self, "txt_declaration"):
            return
        self.txt_declaration.setPlainText(comp.declaration or "We declare that this invoice shows the actual price of the goods described and that all particulars are true and correct.")
        self.txt_terms_quotation.setPlainText(comp.terms_quotation or "1. Validity: 30 days from date of quotation.\n2. Payment: 100% against delivery.\n3. Taxes: GST extra as applicable.")
        self.txt_terms_po.setPlainText(comp.terms_po or "1. Quote PO number on all invoices and delivery challans.\n2. Goods subject to inspection and approval.")
        self.txt_terms_proforma.setPlainText(comp.terms_proforma or "Goods will be dispatched immediately upon receipt of full payment.")
        self.txt_notes_challan.setPlainText(comp.notes_challan or "Goods sent on approval/job work basis. Not for sale.")

        num_fmt = comp.number_format or "Indian"
        idx = self.combo_num_fmt.findData(num_fmt)
        if idx >= 0:
            self.combo_num_fmt.setCurrentIndex(idx)

        self.chk_print_all_copies.setChecked(bool(getattr(comp, "print_all_copies", False)))
        self.chk_print_hsn_summary.setChecked(bool(getattr(comp, "print_hsn_summary", True)))
        self.chk_show_value_on_challan.setChecked(bool(getattr(comp, "show_value_on_challan", False)))
        self.chk_adaptive_font.setChecked(bool(getattr(comp, "adaptive_item_font_enabled", True)))
        self.spn_font_max.setValue(float(getattr(comp, "adaptive_item_font_max", 13.0) or 13.0))
        self.spn_font_min.setValue(float(getattr(comp, "adaptive_item_font_min", 7.5) or 7.5))
        self._on_adaptive_font_toggled(self.chk_adaptive_font.isChecked())

        if comp.seal_path and Path(comp.seal_path).exists():
            self.current_seal_path = comp.seal_path
            self.lbl_seal_path.setText(Path(comp.seal_path).name)
        else:
            self.current_seal_path = None
            self.lbl_seal_path.setText("No seal selected")

        if comp.signature_path and Path(comp.signature_path).exists():
            self.current_sig_path = comp.signature_path
            self.lbl_sig_path.setText(Path(comp.signature_path).name)
        else:
            self.current_sig_path = None
            self.lbl_sig_path.setText("No signature selected")

        if hasattr(self, "chk_ask_save"):
            from app.ui.save_dialog import get_export_settings
            res = get_export_settings()
            if isinstance(res, (tuple, list)):
                ask_every_time = res[0] if len(res) > 0 else True
                default_folder = res[1] if len(res) > 1 else ""
            elif isinstance(res, dict):
                ask_every_time = res.get("ask_every_time", True)
                default_folder = res.get("default_folder", "")
            else:
                ask_every_time, default_folder = True, ""
            self.chk_ask_save.setChecked(bool(ask_every_time))
            self.inp_export_folder.setText(str(default_folder or ""))

    def _browse_default_export_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Default Export Folder", self.inp_export_folder.text())
        if folder:
            self.inp_export_folder.setText(folder)

    def _on_adaptive_font_toggled(self, checked: bool):
        self.spn_font_max.setEnabled(checked)
        self.spn_font_min.setEnabled(checked)

    def save_pdf_suite_settings(self):
        min_sz = self.spn_font_min.value()
        max_sz = self.spn_font_max.value()
        if self.chk_adaptive_font.isChecked():
            if min_sz < 6.0 or max_sz > 16.0:
                ThemedMessageBox.warning(
                    self,
                    "Invalid Font Range",
                    "Adaptive item text font sizes must be within 6.0 pt and 16.0 pt."
                )
                return
            if min_sz >= max_sz:
                ThemedMessageBox.warning(
                    self,
                    "Invalid Font Range",
                    "Smallest item text size must be strictly less than Largest item text size."
                )
                return

        with get_session() as session:
            comp = session.query(CompanyProfile).first()
            if not comp:
                comp = CompanyProfile()
                session.add(comp)

            comp.declaration = self.txt_declaration.toPlainText().strip()
            comp.terms_quotation = self.txt_terms_quotation.toPlainText().strip()
            comp.terms_po = self.txt_terms_po.toPlainText().strip()
            comp.terms_proforma = self.txt_terms_proforma.toPlainText().strip()
            comp.notes_challan = self.txt_notes_challan.toPlainText().strip()

            comp.number_format = self.combo_num_fmt.currentData() or "Indian"
            comp.print_all_copies = self.chk_print_all_copies.isChecked()
            comp.print_hsn_summary = self.chk_print_hsn_summary.isChecked()
            comp.show_value_on_challan = self.chk_show_value_on_challan.isChecked()
            comp.adaptive_item_font_enabled = self.chk_adaptive_font.isChecked()
            comp.adaptive_item_font_max = Decimal(str(round(max_sz, 2)))
            comp.adaptive_item_font_min = Decimal(str(round(min_sz, 2)))

            comp.seal_path = self.current_seal_path
            comp.signature_path = self.current_sig_path
            session.commit()

        if hasattr(self, "chk_ask_save"):
            from app.ui.save_dialog import set_export_settings
            set_export_settings(
                ask_every_time=self.chk_ask_save.isChecked(),
                default_folder=self.inp_export_folder.text().strip()
            )

        ThemedMessageBox.information(self, "Success", "PDF Document Suite settings saved successfully!")
        self.profile_updated.emit()

    # ==========================================
    # Tab 2: Backup & Database Management
    # ==========================================
    def init_backup_tab(self):
        layout = QVBoxLayout(self.tab_backup)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(16)

        # Info Card
        info_card = CardFrame()
        ic_layout = QVBoxLayout(info_card)
        ic_layout.setSpacing(8)

        db_size_kb = DB_PATH.stat().st_size / 1024 if DB_PATH.exists() else 0
        lbl_info = QLabel(
            f"<b>Database Location:</b> {DB_PATH}<br/>"
            f"<b>Database Engine:</b> SQLite 3 with WAL Mode (Zero Server Dependency)<br/>"
            f"<b>Current DB Size:</b> {db_size_kb:,.1f} KB<br/>"
            f"<b>Backup Directory:</b> {BACKUP_DIR}"
        )
        lbl_info.setFont(theme_manager.font("body"))
        ic_layout.addWidget(lbl_info)
        layout.addWidget(info_card)

        # Action Buttons
        btn_box = QHBoxLayout()
        btn_box.setSpacing(12)

        self.btn_create_backup = QPushButton("Create Instant Backup Now")
        self.btn_create_backup.setProperty("variant", "primary")
        self.btn_create_backup.setIcon(theme_manager.icon("download", color_token="text_on_accent", size=16))
        self.btn_create_backup.clicked.connect(self.handle_backup)
        btn_box.addWidget(self.btn_create_backup)

        self.btn_restore = QPushButton("Restore Database from Backup")
        self.btn_restore.setProperty("variant", "secondary")
        self.btn_restore.setIcon(theme_manager.icon("refresh", size=16))
        self.btn_restore.clicked.connect(self.handle_restore)
        btn_box.addWidget(self.btn_restore)

        btn_sample = QPushButton("Seed Sample Demo Data")
        btn_sample.setProperty("variant", "secondary")
        btn_sample.setIcon(theme_manager.icon("plus", size=16))
        btn_sample.clicked.connect(self.handle_sample_data)
        btn_box.addWidget(btn_sample)

        btn_clear = QPushButton("Wipe All Business Data")
        btn_clear.setProperty("variant", "danger")
        btn_clear.setIcon(theme_manager.icon("trash", color_token="text_on_accent", size=16))
        btn_clear.clicked.connect(self.handle_clear_data)
        btn_box.addWidget(btn_clear)

        btn_factory = QPushButton("Reset to Factory Settings")
        btn_factory.setProperty("variant", "danger")
        btn_factory.setIcon(theme_manager.icon("refresh", color_token="text_on_accent", size=16))
        btn_factory.clicked.connect(self.handle_factory_reset)
        btn_box.addWidget(btn_factory)

        layout.addLayout(btn_box)
        layout.addStretch()

    def handle_backup(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Choose Backup Destination Folder",
            str(BACKUP_DIR)
        )
        if not folder:
            return

        def _on_success(b_path):
            ThemedMessageBox.information(self, "Backup Successful", f"Full database backup created at:\n{b_path}")

        def _on_error(e):
            ThemedMessageBox.critical(self, "Backup Failed", f"Error creating backup: {e}")

        run_in_background(
            create_backup,
            on_result=_on_success,
            on_error=_on_error,
            trigger_button=self.btn_create_backup,
            custom_dest_dir=Path(folder)
        )

    def handle_restore(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Backup File to Restore",
            str(BACKUP_DIR), "SQLite DB Files (*.db *.sqlite);;All Files (*.*)"
        )
        if not file_path:
            return

        confirmed = ThemedMessageBox.question(
            self, "Confirm Restore",
            "Restoring will overwrite your current active database with the selected backup.\nDo you want to proceed?"
        )
        if confirmed:
            def _on_success(_):
                ThemedMessageBox.information(
                    self, "Restored",
                    "Database restored successfully! Please restart application to ensure cached states are refreshed."
                )

            def _on_error(e):
                ThemedMessageBox.critical(self, "Restore Error", f"Failed to restore: {e}")

            run_in_background(
                restore_backup,
                on_result=_on_success,
                on_error=_on_error,
                trigger_button=self.btn_restore,
                backup_file_path=Path(file_path)
            )

    def handle_sample_data(self):
        confirmed = ThemedMessageBox.question(
            self, "Seed Demo Data",
            "This will reset all party masters and transactions with sample B2B trading data for demonstration.\nAre you sure?"
        )
        if confirmed:
            try:
                populate_sample_data(force=True)
                ThemedMessageBox.information(
                    self, "Sample Data Populated",
                    "Sample trading parties and transactions generated successfully!"
                )
                self.profile_updated.emit()
            except Exception as e:
                ThemedMessageBox.critical(self, "Error", f"Failed to populate sample data: {e}")

    def handle_clear_data(self):
        confirmed = ThemedMessageBox.question(
            self, "Confirm Wipe All Data",
            "This will permanently delete ALL parties, products, vouchers, invoices, quotations, POs, expenses, and transactions from the database.\n\n"
            "This action cannot be undone. Do you want to proceed?"
        )
        if confirmed:
            try:
                clear_all_business_data()
                ThemedMessageBox.information(
                    self, "Data Wiped Clean",
                    "All dummy and business records have been permanently cleared. The database is now ready for your real data."
                )
                self.load_company_profile()
                self.profile_updated.emit()
            except Exception as e:
                ThemedMessageBox.critical(self, "Error", f"Failed to clear data: {e}")

    def handle_factory_reset(self):
        confirmed = ThemedMessageBox.question(
            self, "Reset to Factory Settings",
            "This will reset your Company Profile, terms, and export preferences to a brand-new factory state.\n\n"
            "Would you like to proceed?"
        )
        if not confirmed:
            return

        backup_first = ThemedMessageBox.question(
            self, "Create Safety Backup?",
            "Would you like to generate an instant database safety backup before resetting?"
        )
        if backup_first:
            try:
                b_path = create_backup()
                ThemedMessageBox.information(self, "Backup Saved", f"Safety backup created at:\n{b_path}")
            except Exception as e:
                ThemedMessageBox.warning(self, "Backup Warning", f"Could not create backup: {e}")

        second_confirm = ThemedMessageBox.question(
            self, "Final Confirmation",
            "Are you completely sure? This will wipe your company profile identity and revert all settings to factory default."
        )
        if second_confirm:
            try:
                with get_session() as session:
                    comp = session.query(CompanyProfile).first()
                    if comp:
                        comp.name = ""
                        comp.trade_name = None
                        comp.gstin = None
                        comp.pan = None
                        comp.address = None
                        comp.city = None
                        comp.state = None
                        comp.state_code = None
                        comp.pincode = None
                        comp.phone = None
                        comp.email = None
                        comp.bank_name = None
                        comp.bank_account_no = None
                        comp.bank_ifsc = None
                        comp.bank_branch = None
                        comp.upi_id = None
                        comp.logo_path = None
                        comp.seal_path = None
                        comp.signature_path = None
                        session.commit()
                from app.ui.save_dialog import set_export_settings
                set_export_settings(ask_every_time=True, default_folder="")
                self.load_company_profile()
                self.profile_updated.emit()
                ThemedMessageBox.information(self, "Factory Reset", "Settings have been restored to factory clean state.")
            except Exception as e:
                ThemedMessageBox.critical(self, "Error", f"Failed to reset settings: {e}")

    # ==========================================
    # Tab 3: Offline Licensing
    # ==========================================
    def init_license_tab(self):
        layout = QVBoxLayout(self.tab_license)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(14)

        lic = get_license_status()

        # Status Card
        stat_card = CardFrame()
        sc_layout = QVBoxLayout(stat_card)
        sc_layout.setSpacing(8)

        status_text = "LICENSED" if lic["is_licensed"] else "EVALUATION"
        badge = StatusBadgeLabel(status_text)

        status_row = QHBoxLayout()
        lbl_status_title = QLabel("License Status:")
        lbl_status_title.setFont(theme_manager.font("subtitle"))
        status_row.addWidget(lbl_status_title)
        status_row.addWidget(badge)
        status_row.addStretch()
        sc_layout.addLayout(status_row)

        self.lbl_lic_status = QLabel(
            f"<b>Hardware Machine ID:</b> <code>{lic['machine_id']}</code><br/>"
            f"<b>Licensed To:</b> {lic.get('issued_to') or 'Unregistered / Evaluation Mode'}"
        )
        self.lbl_lic_status.setFont(theme_manager.font("body"))
        sc_layout.addWidget(self.lbl_lic_status)
        layout.addWidget(stat_card)

        # Activation Form
        form_frame = CardFrame()
        f_layout = QFormLayout(form_frame)
        f_layout.setSpacing(10)

        # Copy Machine ID button
        m_box = QHBoxLayout()
        self.lbl_m_val = QLabel(lic["machine_id"])
        self.lbl_m_val.setFont(theme_manager.font("tabular"))
        self.lbl_m_val.setProperty("variant", "subtitle")

        btn_copy_m = QPushButton("Copy Machine ID")
        btn_copy_m.setProperty("variant", "secondary")
        btn_copy_m.setIcon(theme_manager.icon("file_text", size=14))
        btn_copy_m.clicked.connect(
            lambda: [QApplication.clipboard().setText(lic["machine_id"]),
                     ThemedMessageBox.information(self, "Copied", "Machine ID copied to clipboard!")]
        )
        m_box.addWidget(self.lbl_m_val)
        m_box.addWidget(btn_copy_m)
        m_box.addStretch()
        f_layout.addRow("Your Machine ID:", m_box)

        self.inp_lic_comp = QLineEdit()
        self.inp_lic_comp.setPlaceholderText("Enter Registered Company Name exactly as provided by vendor")
        f_layout.addRow("Registered Company *:", self.inp_lic_comp)

        self.inp_lic_key = QLineEdit()
        self.inp_lic_key.setPlaceholderText("e.g. P-4B92-7E1A-88D1-9F2B")
        f_layout.addRow("Activation Key *:", self.inp_lic_key)

        layout.addWidget(form_frame)

        btn_activate = QPushButton("Activate Commercial License")
        btn_activate.setProperty("variant", "primary")
        btn_activate.setIcon(theme_manager.icon("check", color_token="text_on_accent", size=16))
        btn_activate.clicked.connect(self.handle_activation)
        layout.addWidget(btn_activate, alignment=Qt.AlignRight)

        layout.addStretch()

    def handle_activation(self):
        cname = self.inp_lic_comp.text().strip()
        key = self.inp_lic_key.text().strip()
        if not cname or not key:
            ThemedMessageBox.warning(self, "Validation Error", "Please provide Company Name and Activation Key.")
            return

        success, msg = activate_license(cname, key)
        if success:
            ThemedMessageBox.information(
                self, "License Activated",
                "Congratulations! Your commercial license has been activated successfully on this PC."
            )
            lic = get_license_status()
            self.lbl_lic_status.setText(
                f"<b>Hardware Machine ID:</b> <code>{lic['machine_id']}</code><br/>"
                f"<b>Licensed To:</b> {lic.get('issued_to')}"
            )
        else:
            ThemedMessageBox.critical(self, "Activation Failed", f"License key verification failed:\n{msg}")

    # ==========================================
    # Tab 4: System Diagnostics & Crash Logs
    # ==========================================
    def init_diagnostics_tab(self):
        layout = QVBoxLayout(self.tab_diagnostics)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(14)

        # Health Status Card
        self.health_card = CardFrame()
        hc_layout = QVBoxLayout(self.health_card)
        self.lbl_health_info = QLabel("Click 'Run Health Check' to inspect system memory, threads, and SQLite latency.")
        self.lbl_health_info.setFont(theme_manager.font("body"))
        hc_layout.addWidget(self.lbl_health_info)
        layout.addWidget(self.health_card)

        # Action buttons
        btn_box = QHBoxLayout()
        btn_box.setSpacing(10)

        btn_run_check = QPushButton("Run Live Health Check")
        btn_run_check.setProperty("variant", "primary")
        btn_run_check.setIcon(theme_manager.icon("refresh", color_token="text_on_accent", size=16))
        btn_run_check.clicked.connect(self.run_health_check_ui)
        btn_box.addWidget(btn_run_check)

        btn_thread_dump = QPushButton("Generate Thread Dump")
        btn_thread_dump.setProperty("variant", "secondary")
        btn_thread_dump.setIcon(theme_manager.icon("file_text", size=16))
        btn_thread_dump.clicked.connect(self.generate_thread_dump_ui)
        btn_box.addWidget(btn_thread_dump)

        btn_open_logs = QPushButton("Open Logs Folder")
        btn_open_logs.setProperty("variant", "secondary")
        btn_open_logs.setIcon(theme_manager.icon("file_text", size=16))
        btn_open_logs.clicked.connect(self.open_logs_folder_ui)
        btn_box.addWidget(btn_open_logs)

        btn_export_diag = QPushButton("Export Diagnostics (Zip)")
        btn_export_diag.setProperty("variant", "secondary")
        btn_export_diag.setIcon(theme_manager.icon("download", size=16))
        btn_export_diag.clicked.connect(self.export_diagnostics_bundle_ui)
        btn_box.addWidget(btn_export_diag)

        btn_box.addStretch()
        layout.addLayout(btn_box)

        # Log Viewer Section
        viewer_frame = CardFrame()
        vf_layout = QVBoxLayout(viewer_frame)
        vf_layout.setContentsMargins(10, 10, 10, 10)
        vf_layout.setSpacing(8)

        v_top = QHBoxLayout()
        v_top.addWidget(QLabel("<b>Log File:</b>"))
        self.combo_log_file = QComboBox()
        self.combo_log_file.addItems([
            "billflow.log (Application Event Log)",
            "app.log (Legacy Event Log)",
            "crash.log (Fatal Crash Traces)",
            "thread_dump.log (Thread Stack Traces)"
        ])
        self.combo_log_file.currentIndexChanged.connect(self.refresh_log_viewer_ui)
        v_top.addWidget(self.combo_log_file)

        btn_refresh_log = QPushButton("Refresh Log")
        btn_refresh_log.setProperty("variant", "secondary")
        btn_refresh_log.setIcon(theme_manager.icon("refresh", size=14))
        btn_refresh_log.clicked.connect(self.refresh_log_viewer_ui)
        v_top.addWidget(btn_refresh_log)

        v_top.addStretch()
        vf_layout.addLayout(v_top)

        self.txt_log_content = QPlainTextEdit()
        self.txt_log_content.setReadOnly(True)
        self.txt_log_content.setFont(theme_manager.font("tabular"))
        vf_layout.addWidget(self.txt_log_content, 1)

        layout.addWidget(viewer_frame, 1)

        # Run health check initially
        self.run_health_check_ui()

    def run_health_check_ui(self):
        report = run_system_health_check()
        db = report.get("db", {})
        status_col = theme_manager.color("success") if report["status"] == "HEALTHY" else theme_manager.color("danger")
        warn_html = "<br/>".join(f"• {w}" for w in report.get("warnings", [])) if report.get("warnings") else "None (Optimal)"

        self.lbl_health_info.setText(
            f"<b>Status:</b> <span style='color: {status_col}; font-weight:bold;'>{report['status']}</span> | "
            f"<b>PID:</b> {report['pid']} | "
            f"<b>Python:</b> {report['python_version']} ({report['platform']})<br/>"
            f"<b>Process RAM:</b> {report['memory_mb']} MB | "
            f"<b>Active Threads:</b> {report['active_threads']} | "
            f"<b>App Log Size:</b> {report.get('log_file_size_kb', 0)} KB<br/>"
            f"<b>SQLite Mode:</b> {db.get('journal_mode', 'N/A')} | "
            f"<b>Busy Timeout:</b> {db.get('busy_timeout_ms', 'N/A')} ms | "
            f"<b>Integrity:</b> {db.get('integrity', 'N/A')} | "
            f"<b>Query Latency:</b> {db.get('latency_ms', 'N/A')} ms<br/>"
            f"<b>Warnings:</b> {warn_html}"
        )
        self.refresh_log_viewer_ui()

    def generate_thread_dump_ui(self):
        dump_thread_stacks()
        ThemedMessageBox.information(
            self, "Thread Dump Saved",
            f"A snapshot of all running thread stack traces was captured and saved to:\n{LOG_DIR / 'thread_dump.log'}"
        )
        self.combo_log_file.setCurrentIndex(2)
        self.refresh_log_viewer_ui()

    def open_logs_folder_ui(self):
        if not LOG_DIR.exists():
            LOG_DIR.mkdir(parents=True, exist_ok=True)
        try:
            os.startfile(str(LOG_DIR))
        except Exception as e:
            ThemedMessageBox.warning(self, "Open Folder Error", f"Could not open logs folder: {e}")

    def export_diagnostics_bundle_ui(self):
        from app.core.diagnostics import export_diagnostics_bundle
        try:
            bundle_path = export_diagnostics_bundle()
            ThemedMessageBox.information(
                self,
                "Diagnostics Exported",
                f"Diagnostics bundle package created successfully:\n{bundle_path}"
            )
            try:
                os.startfile(os.path.dirname(str(bundle_path)))
            except Exception:
                pass
        except Exception as e:
            ThemedMessageBox.critical(self, "Export Error", f"Failed to export diagnostics bundle: {e}")

    def refresh_log_viewer_ui(self):
        idx = self.combo_log_file.currentIndex()
        filenames = ["billflow.log", "app.log", "crash.log", "thread_dump.log"]
        fname = filenames[idx] if 0 <= idx < len(filenames) else "billflow.log"
        target_path = LOG_DIR / fname

        if not target_path.exists():
            self.txt_log_content.setPlainText(f"File {fname} does not exist yet. No events recorded.")
            return

        try:
            with open(target_path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
                tail = lines[-200:] if len(lines) > 200 else lines
                self.txt_log_content.setPlainText("".join(tail))
                self.txt_log_content.verticalScrollBar().setValue(
                    self.txt_log_content.verticalScrollBar().maximum()
                )
        except Exception as e:
            self.txt_log_content.setPlainText(f"Failed to read {fname}: {e}")
