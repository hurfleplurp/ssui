#!/usr/bin/env python
# -*- coding: utf-8 -*-

import ctypes
import sys
import os
import configparser
import re
from PyQt5.QtWidgets import (QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout, 
                            QHBoxLayout, QLabel, QLineEdit, QSpinBox, QDoubleSpinBox, 
                            QComboBox, QCheckBox, QPushButton, QFileDialog, QMessageBox,
                            QScrollArea, QGridLayout, QGroupBox, QFormLayout, QTextEdit)
from PyQt5.QtCore import Qt, QSettings, QEvent, QSize
from PyQt5.QtGui import QColor, QIcon, QPalette, QPixmap, QKeyEvent
from PyQt5.QtWidgets import QColorDialog


class StyleSwitcherConfigParser(configparser.ConfigParser):
    """Extend ConfigParser to handle StyleSwitcher's BGM array format"""
    

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bgm_data = None

    def optionxform(self, optionstr):
        # Preserve case in option names
        return optionstr
        
    def read(self, filenames, *args, **kwargs):
        """Custom read method to preserve BGM array content"""
        if isinstance(filenames, (str, os.PathLike)):
            filenames = [filenames]
        
        # First, check for BGM array in the file
        for filename in filenames:
            if not os.path.exists(filename):
                continue
            
            with open(filename, 'r') as f:
                content = f.read()
                
            # Extract BGM array content if present
            # Match everything between BGM[] = { and the closing }
            bgm_match = re.search(r'\[SOUND\].*?BGM\[\]\s*=\s*\{(.*?)\}', content, re.DOTALL)
            if bgm_match:
                self.bgm_data = bgm_match.group(1).strip()
            
            # Remove the BGM[] entry from the content to avoid parsing errors
            if bgm_match:
                content_without_bgm = re.sub(r'BGM\[\]\s*=\s*\{.*?\}', '', content, flags=re.DOTALL)
                # Write a temporary file without the BGM array for configparser to read
                temp_filename = f"{filename}.temp"
                with open(temp_filename, 'w') as temp_f:
                    temp_f.write(content_without_bgm)
                
                # Read the modified file and then delete it
                result = super().read([temp_filename], *args, **kwargs)
                try:
                    os.remove(temp_filename)
                except:
                    pass  # Ignore errors when deleting temp file
                return result
        
        # If we didn't handle a BGM array, just do the normal parsing
        return super().read(filenames, *args, **kwargs)
        
    def write(self, fp, space_around_delimiters=True):
        """Custom write method to preserve BGM array format"""
        # If we have BGM array data, we need to manually handle the SOUND section
        if self.bgm_data is not None and 'SOUND' in self:
            # Save a copy of the sound section
            sound_section = dict(self['SOUND'])
            
            # Create the output manually
            sections = list(self.sections())
            for section in sections:
                fp.write(f"[{section}]\n")
                
                if section == 'SOUND':
                    # Write BGM array first with proper formatting
                    fp.write(f"BGM[] = {{\n{self.bgm_data}\n}}\n")
                    
                    # Write other SOUND settings
                    for key, value in sound_section.items():
                        if key != 'BGM[]':  # Skip the array that we already handled
                            fp.write(f"{key}={value}\n")
                else:
                    # Normal section handling
                    for key, value in self[section].items():
                        fp.write(f"{key}={value}\n")
                
                fp.write("\n")
        else:
            # Use default implementation if no BGM data
            super().write(fp, space_around_delimiters)


class StyleSwitcherUI(QMainWindow):
    def __init__(self, app=None):
        super().__init__()
        self.rgbFields = {}
        self.rgbPreviews = {}
        self.keybindFields = {}
        self.keybindLabels = {}
        self.keybindButtons = {}
        self.keybindKinds = {}
        self.activeKeybindKey = None
        self.activeKeybindButton = None
        if app is not None:
            self.applyDarkTheme(app)
            app.installEventFilter(self)
        self.initUI()
        self.config = None
        self.iniFile = None
        
    def initUI(self):
        self.setWindowTitle("StyleSwitcher Configuration")
        self.setMinimumSize(800, 600)
        
        # Main widget and layout
        mainWidget = QWidget()
        self.setCentralWidget(mainWidget)
        mainLayout = QVBoxLayout(mainWidget)
        
        # Create tab widget
        self.tabs = QTabWidget()
        
        # Create tabs
        self.createDisplayTab()
        self.createGameTab()
        self.createInputTab()
        self.createSoundTab()
        self.createSystemTab()
        
        mainLayout.addWidget(self.tabs)
          # Create buttons
        buttonLayout = QHBoxLayout()
        self.openButton = QPushButton("Open Config")
        self.saveButton = QPushButton("Save Config")
        self.saveAsButton = QPushButton("Save As...")
        self.openButton.clicked.connect(self.loadConfig)
        self.saveButton.clicked.connect(self.saveConfig)
        self.saveAsButton.clicked.connect(self.saveConfigAs)
        
        buttonLayout.addWidget(self.openButton)
        buttonLayout.addWidget(self.saveButton)
        buttonLayout.addWidget(self.saveAsButton)
        
        mainLayout.addLayout(buttonLayout)
        
        # Try to load default config file
        default_config = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "StyleSwitcher.ini")
        if os.path.exists(default_config):
            self.loadConfigFromFile(default_config)
            
    def createScrollableGroupLayout(self, title):
        """Helper to create a group with form layout that expands to fit content"""
        groupBox = QGroupBox(title)
        
        # Create form layout directly in the group box
        layout = QFormLayout(groupBox)
        layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        layout.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        layout.setSpacing(8)  # Add spacing between elements
        layout.setContentsMargins(10, 20, 10, 10)
        
        return groupBox, layout

    def createRgbColorRow(self, color_key, layout):
        """Create a color input row with a live swatch and picker button."""
        rowWidget = QWidget()
        rowLayout = QHBoxLayout(rowWidget)
        rowLayout.setContentsMargins(0, 0, 0, 0)
        rowLayout.setSpacing(8)

        field = QLineEdit()
        field.setPlaceholderText("RRGGBB (hex)")
        field.textChanged.connect(lambda _text, key=color_key: self.updateColorPreview(key))

        preview = QPushButton()
        preview.setFixedSize(24, 24)
        preview.setIconSize(QSize(20, 20))
        preview.setToolTip("Click to choose a color")
        preview.clicked.connect(lambda _checked=False, key=color_key: self.pickColor(key))

        rowLayout.addWidget(field, 1)
        rowLayout.addWidget(preview)

        self.rgbFields[color_key] = field
        self.rgbPreviews[color_key] = preview

        layout.addRow(f"{color_key}:", rowWidget)
        self.updateColorPreview(color_key)

    def createColorSwatchPixmap(self, color):
        """Build a small square pixmap for a color preview swatch."""
        pixmap = QPixmap(20, 20)
        pixmap.fill(color)
        return pixmap

    def updateColorPreview(self, color_key):
        """Refresh the preview swatch for a hex color field."""
        field = self.rgbFields.get(color_key)
        preview = self.rgbPreviews.get(color_key)
        if not field or not preview:
            return

        color_text = field.text().strip().lstrip("#")
        if re.fullmatch(r"[0-9a-fA-F]{6}", color_text):
            color = QColor(f"#{color_text}")
            preview.setIcon(QIcon(self.createColorSwatchPixmap(color)))
            preview.setToolTip(f"#{color_text.upper()}")
        else:
            preview.setIcon(QIcon(self.createColorSwatchPixmap(QColor("#303030"))))
            preview.setToolTip("Enter a valid 6-digit hex color")

    def pickColor(self, color_key):
        """Open a color picker dialog for a hex color field."""
        field = self.rgbFields.get(color_key)
        if not field:
            return

        current_text = field.text().strip().lstrip("#")
        initial_color = QColor(f"#{current_text}") if re.fullmatch(r"[0-9a-fA-F]{6}", current_text) else QColor("#ffffff")
        selected_color = QColorDialog.getColor(initial_color, self, f"Select {color_key}")
        if selected_color.isValid():
            field.setText(selected_color.name()[1:].upper())

    def createKeybindRow(self, field_key, layout, field, binding_kind="single", listenable=True, placeholder=""):
        """Create a keybind row with a code field, a human-readable label, and an optional listen button."""
        rowWidget = QWidget()
        rowLayout = QHBoxLayout(rowWidget)
        rowLayout.setContentsMargins(0, 0, 0, 0)
        rowLayout.setSpacing(8)

        field.setPlaceholderText(placeholder)
        field.textChanged.connect(lambda _text, key=field_key: self.updateKeybindDisplay(key))

        bindingLabel = QLabel()
        bindingLabel.setMinimumWidth(220)
        bindingLabel.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        rowLayout.addWidget(field, 1)
        rowLayout.addWidget(bindingLabel)

        if listenable:
            listenButton = QPushButton("Listen")
            listenButton.setToolTip("Click, then press the key you want to bind")
            listenButton.clicked.connect(lambda _checked=False, key=field_key: self.beginKeybindCapture(key))
            rowLayout.addWidget(listenButton)
            self.keybindButtons[field_key] = listenButton

        self.keybindFields[field_key] = field
        self.keybindLabels[field_key] = bindingLabel
        self.keybindKinds[field_key] = binding_kind

        layout.addRow(f"{field_key}:", rowWidget)
        self.updateKeybindDisplay(field_key)

    def beginKeybindCapture(self, field_key):
        """Start listening for the next key press for the given field."""
        if self.activeKeybindButton:
            self.activeKeybindButton.setText("Listen")
        self.activeKeybindKey = field_key
        self.activeKeybindButton = self.keybindButtons.get(field_key)
        if self.activeKeybindButton:
            self.activeKeybindButton.setText("Press key...")
            self.activeKeybindButton.setEnabled(True)

    def finishKeybindCapture(self):
        """Stop listening for key presses and restore the listen button label."""
        if self.activeKeybindButton:
            self.activeKeybindButton.setText("Listen")
        self.activeKeybindKey = None
        self.activeKeybindButton = None

    def eventFilter(self, a0, a1):
        if self.activeKeybindKey and isinstance(a1, QKeyEvent) and a1.type() == QEvent.Type.KeyPress:
            if a1.isAutoRepeat():
                return True

            if a1.key() == Qt.Key.Key_Escape:
                self.finishKeybindCapture()
                return True

            key_code = self.getNativeVirtualKey(a1)
            if key_code:
                self.applyCapturedKeybind(self.activeKeybindKey, key_code)
                return True

        return super().eventFilter(a0, a1)

    def getNativeVirtualKey(self, event):
        """Return the platform virtual-key code for a Qt key event when available."""
        key_code = 0
        try:
            key_code = int(event.nativeVirtualKey())
        except Exception:
            key_code = 0

        if not key_code:
            key_code = int(event.key())

        return key_code

    def applyCapturedKeybind(self, field_key, key_code):
        """Write the captured key code back to the right field format."""
        field = self.keybindFields.get(field_key)
        if not field:
            self.finishKeybindCapture()
            return

        binding_kind = self.keybindKinds.get(field_key, "single")
        if binding_kind == "pair":
            hex_code = self.formatHexKeyCode(key_code)
            field.setText(f"{hex_code},{hex_code}")
        else:
            field.setText(self.formatHexKeyCode(key_code))

        self.finishKeybindCapture()

    def formatHexKeyCode(self, key_code):
        """Format a virtual-key code as the hex string used by the config file."""
        return f"{key_code:X}"

    def parseHexCode(self, value):
        """Parse a hex code field value into an integer, accepting an optional 0x prefix."""
        value = value.strip()
        if not value:
            return None

        try:
            if value.lower().startswith("0x"):
                return int(value, 0)
            return int(value, 16)
        except ValueError:
            try:
                return int(value, 16)
            except ValueError:
                return None

    def getKeyNameForCode(self, key_code):
        """Convert a virtual-key code to a readable key name."""
        if key_code is None:
            return ""

        if key_code == 0:
            return "Disabled"

        key_name = self.getWindowsKeyName(key_code)
        if key_name:
            return key_name

        fallback_names = {
            0x08: "Backspace",
            0x09: "Tab",
            0x0D: "Enter",
            0x10: "Shift",
            0x11: "Ctrl",
            0x12: "Alt",
            0x13: "Pause",
            0x14: "Caps Lock",
            0x1B: "Esc",
            0x20: "Space",
            0x21: "Page Up",
            0x22: "Page Down",
            0x23: "End",
            0x24: "Home",
            0x25: "Left",
            0x26: "Up",
            0x27: "Right",
            0x28: "Down",
            0x2C: "Print Screen",
            0x2D: "Insert",
            0x2E: "Delete",
        }
        if 0x30 <= key_code <= 0x39:
            return chr(key_code)
        if 0x41 <= key_code <= 0x5A:
            return chr(key_code)
        if 0x60 <= key_code <= 0x69:
            return f"Num {key_code - 0x60}"
        if 0x70 <= key_code <= 0x87:
            return f"F{key_code - 0x6F}"
        return fallback_names.get(key_code, f"0x{key_code:X}")

    def getWindowsKeyName(self, key_code):
        """Use the Windows API to resolve a key code to a localized key name."""
        if os.name != "nt":
            return ""

        try:
            user32 = ctypes.windll.user32
            map_virtual_key = ctypes.windll.user32.MapVirtualKeyW
            scan_code = map_virtual_key(key_code, 0)
            if not scan_code:
                return ""

            lparam = scan_code << 16
            if key_code in (0x25, 0x26, 0x27, 0x28, 0x2D, 0x2E):
                lparam |= 1 << 24

            buffer = ctypes.create_unicode_buffer(128)
            if user32.GetKeyNameTextW(lparam, buffer, len(buffer)):
                return buffer.value
        except Exception:
            return ""

        return ""

    def updateKeybindDisplay(self, field_key):
        """Update the readable binding text for a keybind field."""
        field = self.keybindFields.get(field_key)
        label = self.keybindLabels.get(field_key)
        if not field or not label:
            return

        binding_kind = self.keybindKinds.get(field_key, "single")
        raw_text = field.text().strip()
        if not raw_text:
            label.setText("Not set")
            return

        if binding_kind == "pair":
            parts = [part.strip() for part in raw_text.split(",") if part.strip()]
            if len(parts) != 2:
                label.setText("Invalid binding")
                return

            first_code = self.parseHexCode(parts[0])
            second_code = self.parseHexCode(parts[1])
            first_name = self.getKeyNameForCode(first_code)
            second_name = self.getKeyNameForCode(second_code)
            label.setText(f"In game: {first_name} | Menu: {second_name}")
            return

        code = self.parseHexCode(raw_text)
        if code is None:
            label.setText("Invalid binding")
            return

        if binding_kind == "command":
            label.setText(f"Command id: {self.getCommandDescription(code)}")
        else:
            label.setText(f"Bound to: {self.getKeyNameForCode(code)}")

    def getCommandDescription(self, command_id):
        """Provide a readable label for command-id fields."""
        if command_id == 0x1000:
            return "Reset motion state"
        return f"0x{command_id:X}"

    def applyDarkTheme(self, app):
        """Apply a dark Fusion palette so the app starts in dark mode by default."""
        app.setStyle("Fusion")

        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(45, 45, 45))
        palette.setColor(QPalette.WindowText, QColor("#ffffff"))
        palette.setColor(QPalette.Base, QColor(30, 30, 30))
        palette.setColor(QPalette.AlternateBase, QColor(45, 45, 45))
        palette.setColor(QPalette.ToolTipBase, QColor("#ffffff"))
        palette.setColor(QPalette.ToolTipText, QColor("#ffffff"))
        palette.setColor(QPalette.Text, QColor("#ffffff"))
        palette.setColor(QPalette.Button, QColor(45, 45, 45))
        palette.setColor(QPalette.ButtonText, QColor("#ffffff"))
        palette.setColor(QPalette.BrightText, QColor("#ff0000"))
        palette.setColor(QPalette.Highlight, QColor(64, 128, 192))
        palette.setColor(QPalette.HighlightedText, QColor("#ffffff"))
        palette.setColor(QPalette.Link, QColor(112, 170, 255))
        app.setPalette(palette)

    def createScrollableTabWidget(self):
        """Helper to create a scrollable tab widget"""
        tabWidget = QWidget()
        scrollArea = QScrollArea()
        scrollArea.setWidgetResizable(True)
        scrollArea.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scrollArea.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scrollArea.setFrameShape(QScrollArea.Shape.NoFrame)
        
        contentWidget = QWidget()
        layout = QVBoxLayout(contentWidget)
        layout.setSpacing(10)  # Add spacing between elements
        
        scrollArea.setWidget(contentWidget)
        tabLayout = QVBoxLayout(tabWidget)
        tabLayout.setContentsMargins(0, 0, 0, 0)
        tabLayout.addWidget(scrollArea)
        
        return tabWidget, layout
        
    def createDisplayTab(self):
        # Display Tab - Using scrollable tab layout
        displayTab, displayLayout = self.createScrollableTabWidget()
        
        # General display settings
        generalGroup, generalLayout = self.createScrollableGroupLayout("General Display Settings")
          # Create fields for each setting based on documentation
        self.displayBloom = QCheckBox("Bloom")
        self.displayBloom.setToolTip("Looks great in most rooms, looks horrible in some rooms.\nYou can toggle it ingame by pressing F5.")
        generalLayout.addRow(self.displayBloom)
        
        self.displayDisableBlurShader = QCheckBox("Disable Blur Shader")
        self.displayDisableBlurShader.setToolTip("Disables blur shader effects for better performance")
        generalLayout.addRow(self.displayDisableBlurShader)
        
        self.displayDisableFogShader = QCheckBox("Disable Fog Shader")
        self.displayDisableFogShader.setToolTip("Disables fog shader effects for better performance")
        generalLayout.addRow(self.displayDisableFogShader)
        
        self.displayDisableShadowEngine = QCheckBox("Disable Shadow Engine")
        self.displayDisableShadowEngine.setToolTip("Disables shadow engine for better performance")
        generalLayout.addRow(self.displayDisableShadowEngine)
        
        # For non-checkbox items, we still need labels
        self.displayFOV = QDoubleSpinBox()
        self.displayFOV.setRange(0.1, 2.0)
        self.displayFOV.setSingleStep(0.1)
        self.displayFOV.setToolTip("Sets the field of view")
        generalLayout.addRow("Field of View:", self.displayFOV)
        
        self.displayGammaCorrection = QCheckBox("Gamma Correction")
        self.displayGammaCorrection.setToolTip("Enables gamma correction for improved visual quality")
        generalLayout.addRow(self.displayGammaCorrection)
        
        self.displayMode = QComboBox()
        self.displayMode.addItems(["Windowed", "Fullscreen"])
        self.displayMode.setToolTip("Select how the game window is displayed")
        generalLayout.addRow("Display Mode:", self.displayMode)
        
        self.displayNoir = QCheckBox("Noir Mode")
        self.displayNoir.setToolTip("Turns models black while keeping most of their effects intact.\nYou can toggle it ingame by pressing F6.")
        generalLayout.addRow(self.displayNoir)
        
        self.displayResolution = QLineEdit()
        self.displayResolution.setPlaceholderText("WidthxHeight@FPS (e.g. 1280x720@60)")
        self.displayResolution.setToolTip("Set resolution and refresh rate (e.g. 1920x1080@60)")
        generalLayout.addRow("Resolution:", self.displayResolution)
        
        displayLayout.addWidget(generalGroup)
        
        # RGB Color settings
        rgbGroup, rgbLayout = self.createScrollableGroupLayout("RGB Color Settings")
        
        # Create RGB color fields
        self.rgbFields = {}
        self.rgbPreviews = {}
        self.rgbButtons = {}
        rgb_colors = [
            "RGB.Rebellion", "RGB.Cerberus", "RGB.AgniRudra", "RGB.Nevan", "RGB.Beowulf",
            "RGB.Sparda", "RGB.Yamato", "RGB.Beowulf.Vergil", "RGB.ForceEdge", "RGB.NeroAngelo",
            "RGB.AirHike.Rebellion", "RGB.AirHike.Cerberus", "RGB.AirHike.AgniRudra",
            "RGB.AirHike.Nevan", "RGB.AirHike.Beowulf", "RGB.SkyStar", "RGB.Ultimate"
        ]
        
        for color in rgb_colors:
            self.createRgbColorRow(color, rgbLayout)
            
        displayLayout.addWidget(rgbGroup)
        
        # UI Position settings
        uiGroup, uiLayout = self.createScrollableGroupLayout("UI Position Settings")
        
        # Create UI position fields
        self.uiFields = {}
        ui_positions = [
            "UI.HP1Frame", "UI.HP1Bar", "UI.HP1Bg", "UI.HP2Frame", "UI.HP2Bar", "UI.HP2Bg",
            "UI.MPGauge", "UI.StyleIcon", "UI.RedOrbCounter", "UI.Timer", "UI.Objective",
            "UI.WeaponIcon1", "UI.WeaponIcon2", "UI.StyleRank", "UI.StyleBar", "UI.RoomText",
            "UI.RoomText.Step", "UI.BossFrame", "UI.BossBar", "UI.BossBg"
        ]
        
        for pos in ui_positions:
            self.uiFields[pos] = QLineEdit()
            self.uiFields[pos].setPlaceholderText("X,Y")
            uiLayout.addRow(f"{pos}:", self.uiFields[pos])
            
        displayLayout.addWidget(uiGroup)
          # Add tab to tabwidget
        self.tabs.addTab(displayTab, "Display")
        
    def createGameTab(self):
        # Game Tab - Using scrollable tab layout
        gameTab, gameLayout = self.createScrollableTabWidget()
          # Core abilities group
        coreGroup, coreLayout = self.createScrollableGroupLayout("Core Abilities")
        self.gameAirHikeCoreAbility = QCheckBox("Air Hike Core Ability")
        self.gameAirHikeCoreAbility.setToolTip("When checked, Air Hike is available without purchasing")
        coreLayout.addRow(self.gameAirHikeCoreAbility)
        
        gameLayout.addWidget(coreGroup)
        
        # Arcade Mode group
        arcadeGroup, arcadeLayout = self.createScrollableGroupLayout("Arcade Mode")
        
        self.gameArcade = QCheckBox("Arcade Mode")
        self.gameArcade.setToolTip("Enables arcade mode for custom gameplay settings")
        arcadeLayout.addRow(self.gameArcade)
        
        self.gameArcadeMission = QSpinBox()
        self.gameArcadeMission.setRange(1, 20)
        arcadeLayout.addRow("Mission:", self.gameArcadeMission)
        
        self.gameArcadeMode = QSpinBox()
        self.gameArcadeMode.setRange(0, 4)
        arcadeLayout.addRow("Mode:", self.gameArcadeMode)
        
        self.gameArcadeAutomatic = QCheckBox("Automatic Mode")
        arcadeLayout.addRow("Automatic:", self.gameArcadeAutomatic)
        
        self.gameArcadeCharacter = QSpinBox()
        self.gameArcadeCharacter.setRange(0, 2)
        arcadeLayout.addRow("Character:", self.gameArcadeCharacter)
        
        self.gameArcadeBloodyPalace = QLineEdit()
        self.gameArcadeBloodyPalace.setPlaceholderText("Floor,Room")
        arcadeLayout.addRow("Bloody Palace:", self.gameArcadeBloodyPalace)
        
        self.gameArcadeEquipment = QLineEdit()
        self.gameArcadeEquipment.setPlaceholderText("Equipment Hex")
        arcadeLayout.addRow("Equipment:", self.gameArcadeEquipment)
        
        self.gameArcadeCostume = QSpinBox()
        self.gameArcadeCostume.setRange(1, 4)
        arcadeLayout.addRow("Costume:", self.gameArcadeCostume)
        
        self.gameArcadeHP = QSpinBox()
        self.gameArcadeHP.setRange(0, 50000)
        self.gameArcadeHP.setSingleStep(1000)
        arcadeLayout.addRow("HP:", self.gameArcadeHP)
        
        self.gameArcadeMP = QSpinBox()
        self.gameArcadeMP.setRange(0, 50000)
        self.gameArcadeMP.setSingleStep(1000)
        arcadeLayout.addRow("MP:", self.gameArcadeMP)
        
        self.gameArcadeStyle = QSpinBox()
        self.gameArcadeStyle.setRange(0, 4)
        arcadeLayout.addRow("Style:", self.gameArcadeStyle)
        
        self.gameArcadeRoom = QSpinBox()
        self.gameArcadeRoom.setRange(0, 100)
        arcadeLayout.addRow("Room:", self.gameArcadeRoom)
        
        self.gameArcadePosition = QSpinBox()
        self.gameArcadePosition.setRange(0, 10)
        arcadeLayout.addRow("Position:", self.gameArcadePosition)
        
        gameLayout.addWidget(arcadeGroup)
          # Artemis group
        artemisGroup, artemisLayout = self.createScrollableGroupLayout("Artemis Settings")
        
        self.gameArtemisInstantCharge = QCheckBox("Instant Charge")
        self.gameArtemisInstantCharge.setToolTip("Makes Artemis charge instantly")
        artemisLayout.addRow(self.gameArtemisInstantCharge)
        
        self.gameArtemisNormalShotMultiLockSwap = QCheckBox("Normal Shot/Multi-Lock Swap")
        self.gameArtemisNormalShotMultiLockSwap.setToolTip("Swaps normal shot and multi-lock functions")
        artemisLayout.addRow(self.gameArtemisNormalShotMultiLockSwap)
        
        gameLayout.addWidget(artemisGroup)
        
        # Boss Rush group
        bossGroup, bossLayout = self.createScrollableGroupLayout("Boss Rush")
        
        self.gameBossRush = QCheckBox("Boss Rush")
        self.gameBossRush.setToolTip("Enables the boss rush mode")
        bossLayout.addRow(self.gameBossRush)
        
        gameLayout.addWidget(bossGroup)
        
        # Devil Mobility group
        devilGroup, devilLayout = self.createScrollableGroupLayout("Devil Mobility")
        
        # Create fields for Devil settings (use spin boxes for numeric values)
        self.devilFields = {}
        devil_settings = [
            "Devil.AirHike", "Devil.WallJump", "Devil.WallRun",
            "Devil.Dash.Lv1", "Devil.Dash.Lv2", "Devil.Dash.Lv3",
            "Devil.SkyStar", "Devil.AirTrick", "Devil.AirTrick.Vergil",
            "Devil.TrickUp", "Devil.TrickDown"
        ]
        for key in devil_settings:
            spin = QSpinBox()
            spin.setRange(0, 10)
            devilLayout.addRow(f"{key}:", spin)
            self.devilFields[key] = spin
        gameLayout.addWidget(devilGroup)
        
        # Human Mobility group
        humanGroup, humanLayout = self.createScrollableGroupLayout("Human Mobility")
        
        self.humanFields = {}
        human_settings = [
            "Human.AirHike", "Human.WallJump", "Human.WallRun",
            "Human.Dash.Lv1", "Human.Dash.Lv2", "Human.Dash.Lv3",
            "Human.SkyStar", "Human.AirTrick", "Human.AirTrick.Vergil",
            "Human.TrickUp", "Human.TrickDown"
        ]
        for key in human_settings:
            spin = QSpinBox()
            spin.setRange(0, 10)
            humanLayout.addRow(f"{key}:", spin)
            self.humanFields[key] = spin
        gameLayout.addWidget(humanGroup)
        # Game Modifiers group
        modifiersGroup, modifiersLayout = self.createScrollableGroupLayout("Game Modifiers")
        self.gameForceEasyAutomaticTwosomeTime = QCheckBox("Force Easy Automatic Twosome Time")
        self.gameForceEasyAutomaticTwosomeTime.setToolTip("Makes Automatic Twosome Time easier to execute")
        modifiersLayout.addRow(self.gameForceEasyAutomaticTwosomeTime)
        self.gameHideBeowulf = QCheckBox("Hide Beowulf")
        self.gameHideBeowulf.setToolTip("Makes Beowulf weapon invisible")
        modifiersLayout.addRow(self.gameHideBeowulf)
        self.gameInfiniteMP = QCheckBox("Infinite MP")
        self.gameInfiniteMP.setToolTip("Provides unlimited magic power")
        modifiersLayout.addRow(self.gameInfiniteMP)
        self.gameInfiniteRainStorm = QCheckBox("Infinite Rain Storm")
        self.gameInfiniteRainStorm.setToolTip("Makes Rain Storm attack last indefinitely")
        modifiersLayout.addRow(self.gameInfiniteRainStorm)
        self.gameInfiniteRoundTrip = QCheckBox("Infinite Round Trip")
        self.gameInfiniteRoundTrip.setToolTip("Makes Round Trip attack last indefinitely")
        modifiersLayout.addRow(self.gameInfiniteRoundTrip)
        self.gameInfiniteSwordPierce = QCheckBox("Infinite Sword Pierce")
        self.gameInfiniteSwordPierce.setToolTip("Makes Sword Pierce attack last indefinitely")
        modifiersLayout.addRow(self.gameInfiniteSwordPierce)
        self.gameLowBuffer = QSpinBox()
        self.gameLowBuffer.setRange(1, 20)
        modifiersLayout.addRow("Low Buffer:", self.gameLowBuffer)
        self.gameMPDeplete = QDoubleSpinBox()
        self.gameMPDeplete.setRange(0, 100)
        self.gameMPDeplete.setSingleStep(1)
        self.gameMPDeplete.setToolTip("Sets the rate at which MP depletes")
        modifiersLayout.addRow("MP Deplete:", self.gameMPDeplete)
        
        self.gameNoDemonForm = QCheckBox("No Demon Form")
        self.gameNoDemonForm.setToolTip("Prevents transformation into demon form")
        modifiersLayout.addRow(self.gameNoDemonForm)
        
        self.gameOrbReach = QSpinBox()
        self.gameOrbReach.setRange(10, 1000)
        self.gameOrbReach.setSingleStep(10)
        self.gameOrbReach.setToolTip("Sets the distance at which orbs can be collected")
        modifiersLayout.addRow("Orb Reach:", self.gameOrbReach)
        
        self.gameRevertDelay = QSpinBox()
        self.gameRevertDelay.setRange(0, 200)
        self.gameRevertDelay.setToolTip("Sets the delay before reverting from demon form")
        modifiersLayout.addRow("Revert Delay:", self.gameRevertDelay)
        
        gameLayout.addWidget(modifiersGroup)
        
        # Speed Settings group
        speedGroup, speedLayout = self.createScrollableGroupLayout("Speed Settings")
        
        # Create fields for Speed settings matching INI entries
        self.speedFields = {}
        speed_settings = [
            "Speed.Rebellion", "Speed.Cerberus", "Speed.AgniRudra", "Speed.Nevan",
            "Speed.Beowulf", "Speed.Yamato", "Speed.Beowulf.Vergil", "Speed.ForceEdge",
            "Speed.Yamato.NeroAngelo", "Speed.Beowulf.NeroAngelo"
        ]
        for key in speed_settings:
            spin = QDoubleSpinBox()
            spin.setRange(0.1, 10.0)
            spin.setSingleStep(0.05)
            spin.setValue(1.0)
            speedLayout.addRow(f"{key}:", spin)
            self.speedFields[key] = spin
        gameLayout.addWidget(speedGroup)
          # Style Switcher group
        styleGroup, styleLayout = self.createScrollableGroupLayout("Style Switcher")
        
        self.gameStyleSwitcher = QCheckBox("Style Switcher")
        self.gameStyleSwitcher.setToolTip("Enables style switching during gameplay")
        styleLayout.addRow(self.gameStyleSwitcher)
        
        self.gameStyleSwitcherCancel = QLineEdit()
        self.gameStyleSwitcherCancel.setPlaceholderText("0x1000")
        self.gameStyleSwitcherCancel.setToolTip("Sets the key code for cancelling style actions")
        self.createKeybindRow(
            "StyleSwitcher.Cancel",
            styleLayout,
            self.gameStyleSwitcherCancel,
            binding_kind="command",
            listenable=False,
            placeholder="0x1000",
        )
        
        self.gameStyleSwitcherChronoSwords = QCheckBox("Chrono Swords")
        self.gameStyleSwitcherChronoSwords.setToolTip("Enables Chrono Swords feature")
        styleLayout.addRow(self.gameStyleSwitcherChronoSwords)
        
        self.gameStyleSwitcherNoDoubleTap = QCheckBox("No Double Tap")
        self.gameStyleSwitcherNoDoubleTap.setToolTip("Disables double tap requirement for style actions")
        styleLayout.addRow(self.gameStyleSwitcherNoDoubleTap)
        
        gameLayout.addWidget(styleGroup)
          # Weapon Switcher group
        weaponGroup, weaponLayout = self.createScrollableGroupLayout("Weapon Switcher")
        
        self.gameWeaponSwitcher = QCheckBox("Weapon Switcher")
        self.gameWeaponSwitcher.setToolTip("Enables weapon switching during gameplay")
        weaponLayout.addRow(self.gameWeaponSwitcher)
        
        self.gameWeaponSwitcherDevil = QSpinBox()
        self.gameWeaponSwitcherDevil.setRange(0, 10)
        self.gameWeaponSwitcherDevil.setToolTip("Sets the devil arm for weapon switching")
        weaponLayout.addRow("Devil:", self.gameWeaponSwitcherDevil)
        self.gameWeaponSwitcherMelee = QLineEdit()
        self.gameWeaponSwitcherMelee.setPlaceholderText("00,01,02,03,04")
        weaponLayout.addRow("Melee:", self.gameWeaponSwitcherMelee)
        self.gameWeaponSwitcherRanged = QLineEdit()
        self.gameWeaponSwitcherRanged.setPlaceholderText("05,06,07,08,09")
        weaponLayout.addRow("Ranged:", self.gameWeaponSwitcherRanged)
        self.gameWeaponSwitcherSword = QSpinBox()
        self.gameWeaponSwitcherSword.setRange(0, 10)
        weaponLayout.addRow("Sword:", self.gameWeaponSwitcherSword)
        self.gameWeaponSwitcherTimeout = QDoubleSpinBox()
        self.gameWeaponSwitcherTimeout.setRange(0.1, 20.0)
        self.gameWeaponSwitcherTimeout.setSingleStep(0.1)
        weaponLayout.addRow("Timeout:", self.gameWeaponSwitcherTimeout)
        gameLayout.addWidget(weaponGroup)
        
        # Add tab to tabwidget
        self.tabs.addTab(gameTab, "Game")
        
    def createInputTab(self):
        # Input Tab - Using scrollable tab layout
        inputTab, inputLayout = self.createScrollableTabWidget()
        # Input Settings Group
        inputGroup, inputGroupLayout = self.createScrollableGroupLayout("Input Settings")
        
        self.inputDisableLockOnToggle = QCheckBox("Disable Lock-On Toggle")
        self.inputDisableLockOnToggle.setToolTip("Disables toggling of lock-on, making it active only while button is pressed")
        inputGroupLayout.addRow(self.inputDisableLockOnToggle)
        
        self.inputHotkeys = QCheckBox("Enable Hotkeys")
        self.inputHotkeys.setToolTip("Enables keyboard hotkey functionality")
        inputGroupLayout.addRow(self.inputHotkeys)
        
        inputLayout.addWidget(inputGroup)
        
        # Hotkey Settings Group
        hotkeyGroup, hotkeyLayout = self.createScrollableGroupLayout("Hotkey Settings")
        
        self.hotkeyFields = {}
        hotkeys = [
            "Hotkeys.RestartRoom", "Hotkeys.NoDeath", "Hotkeys.OneHitKill",
            "Hotkeys.HideHUD", "Hotkeys.Bloom", "Hotkeys.Noir"
        ]
        
        for key in hotkeys:
            self.hotkeyFields[key] = QLineEdit()
            self.createKeybindRow(
                key,
                hotkeyLayout,
                self.hotkeyFields[key],
                binding_kind="single",
                listenable=True,
                placeholder="Hex VK code",
            )
            
        inputLayout.addWidget(hotkeyGroup)
        
        # Keyboard Settings Group
        keyboardGroup, keyboardLayout = self.createScrollableGroupLayout("Keyboard Settings")
        
        self.keyboardFields = {}
        keyboard_keys = [
            "Keyboard.L2", "Keyboard.R2", "Keyboard.L1", "Keyboard.R1", 
            "Keyboard.Triangle", "Keyboard.Circle", "Keyboard.Cross", "Keyboard.Square", 
            "Keyboard.Select", "Keyboard.L3", "Keyboard.R3", "Keyboard.Start", 
            "Keyboard.D-Pad.Up", "Keyboard.D-Pad.Right", "Keyboard.D-Pad.Down", "Keyboard.D-Pad.Left", 
            "Keyboard.LeftAnalogStick.Up", "Keyboard.LeftAnalogStick.Right", "Keyboard.LeftAnalogStick.Down", "Keyboard.LeftAnalogStick.Left", 
            "Keyboard.RightAnalogStick.Up", "Keyboard.RightAnalogStick.Right", "Keyboard.RightAnalogStick.Down", "Keyboard.RightAnalogStick.Left"
        ]
        for key in keyboard_keys:
            self.keyboardFields[key] = QLineEdit()
            self.createKeybindRow(
                key,
                keyboardLayout,
                self.keyboardFields[key],
                binding_kind="pair",
                listenable=True,
                placeholder="In-game hex, menu hex",
            )
        inputLayout.addWidget(keyboardGroup)
        
        # Add tab to tabwidget
        self.tabs.addTab(inputTab, "Input")
        
    def createSoundTab(self):
        # Sound Tab - Using scrollable tab layout
        soundTab, soundLayout = self.createScrollableTabWidget()
        # Sound Settings Group
        soundGroup, soundGroupLayout = self.createScrollableGroupLayout("Sound Settings")
        
        # Sound settings
        self.soundDisableSoundDriver = QCheckBox("Disable Sound Driver")
        self.soundDisableSoundDriver.setToolTip("Disable the sound driver entirely, removing BGM engine related fps drops")
        soundGroupLayout.addRow(self.soundDisableSoundDriver)
        self.soundDisableStageSE = QCheckBox("Disable Stage Sound Effects")
        self.soundDisableStageSE.setToolTip("Disables sound effects related to stages and environments")
        soundGroupLayout.addRow(self.soundDisableStageSE)
        self.soundDisableSystemSE = QCheckBox("Disable System Sound Effects")
        self.soundDisableSystemSE.setToolTip("Disables system-related sound effects like UI sounds")
        soundGroupLayout.addRow(self.soundDisableSystemSE)
        self.soundForceMode0 = QCheckBox("Force Mode 0")
        self.soundForceMode0.setToolTip("Use sound playback mode 0 which has fewer FPS drops")
        soundGroupLayout.addRow(self.soundForceMode0)
        
        # Volume settings
        self.soundVolumeBGM = QSpinBox()
        self.soundVolumeBGM.setRange(0, 100)
        soundGroupLayout.addRow("BGM Volume:", self.soundVolumeBGM)
        self.soundVolumeSE = QSpinBox()
        self.soundVolumeSE.setRange(0, 127)
        soundGroupLayout.addRow("SE Volume:", self.soundVolumeSE)
        soundLayout.addWidget(soundGroup)
        
        # BGM Settings Group (raw INI array editable)
        bgmGroup = QGroupBox("BGM Settings")
        bgmLayout = QVBoxLayout(bgmGroup)
        # Multiline text edit for raw BGM[] array data
        self.bgmTextEdit = QTextEdit()
        self.bgmTextEdit.setPlaceholderText("Paste BGM[] array contents here")
        bgmLayout.addWidget(self.bgmTextEdit)
        soundLayout.addWidget(bgmGroup)
        
        # Add tab to tabwidget
        self.tabs.addTab(soundTab, "Sound")
        
    def createSystemTab(self):        # System Tab - Using scrollable tab layout
        systemTab, systemLayout = self.createScrollableTabWidget()
        
        # System Settings Group
        systemGroup, systemGroupLayout = self.createScrollableGroupLayout("System Settings")
        
        self.systemHideCursor = QCheckBox("Hide Cursor")
        self.systemHideCursor.setToolTip("Hides the mouse cursor during gameplay")
        systemGroupLayout.addRow(self.systemHideCursor)
        
        self.systemInvertCamera = QCheckBox("Invert Camera")
        self.systemInvertCamera.setToolTip("Inverts the camera controls")
        systemGroupLayout.addRow(self.systemInvertCamera)
        
        self.systemLanguage = QComboBox()
        self.systemLanguage.addItems(["English", "Japanese"])
        self.systemLanguage.setToolTip("Sets the game's language")
        systemGroupLayout.addRow("Language:", self.systemLanguage)
        
        self.systemSkipCutscenes = QCheckBox("Skip Cutscenes")
        self.systemSkipCutscenes.setToolTip("Automatically skips all cutscenes")
        systemGroupLayout.addRow(self.systemSkipCutscenes)
        
        self.systemSkipIntro = QCheckBox("Skip Intro")
        self.systemSkipIntro.setToolTip("Automatically skips the intro sequence")
        systemGroupLayout.addRow(self.systemSkipIntro)
        
        self.systemSubtitles = QComboBox()
        self.systemSubtitles.addItems(["None", "English", "French", "German", "Italian", "Spanish", "Japanese"])
        self.systemSubtitles.setToolTip("Sets the language for subtitles")
        systemGroupLayout.addRow("Subtitles:", self.systemSubtitles)
        
        self.systemSubtitlesEnable = QCheckBox("Enable Subtitles")
        self.systemSubtitlesEnable.setToolTip("Enables subtitle display during cutscenes")
        systemGroupLayout.addRow(self.systemSubtitlesEnable)
        
        systemLayout.addWidget(systemGroup)
        
        # Add tab to tabwidget
        self.tabs.addTab(systemTab, "System")
        
    def loadConfig(self):
        """Load a configuration file"""
        options = QFileDialog.Options()
        fileName, _ = QFileDialog.getOpenFileName(self, "Open StyleSwitcher Config", "", 
                                               "INI Files (*.ini);;All Files (*)", options=options)
        if fileName:
            self.loadConfigFromFile(fileName)
    
    def loadConfigFromFile(self, filePath):
        """Load configuration from a file path"""
        try:
            self.iniFile = filePath
            self.config = StyleSwitcherConfigParser(strict=False)
            # optionxform is set in the class already
            self.config.read(filePath)
            self.populateFields()
            self.setWindowTitle(f"StyleSwitcher Configuration - {os.path.basename(filePath)}")
            QMessageBox.information(self, "Success", f"Configuration loaded successfully from {os.path.basename(filePath)}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load configuration: {str(e)}")
            
    def saveConfig(self):
        """Save the configuration to the current file"""
        if not self.iniFile:
            self.saveConfigAs()
            return
        
        try:
            self.updateConfigFromFields()
            if self.config:  # Make sure config exists
                with open(self.iniFile, 'w') as f:
                    self.config.write(f)
                QMessageBox.information(self, "Success", f"Configuration saved to {os.path.basename(self.iniFile)}")
            else:
                QMessageBox.critical(self, "Error", "No configuration loaded to save")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save configuration: {str(e)}")
    
    def saveConfigAs(self):
        """Save the configuration to a new file"""
        options = QFileDialog.Options()
        fileName, _ = QFileDialog.getSaveFileName(self, "Save StyleSwitcher Config", "", 
                                                "INI Files (*.ini);;All Files (*)", options=options)
        if fileName:
            if not fileName.lower().endswith('.ini'):
                fileName += '.ini'
            self.iniFile = fileName
            self.saveConfig()
    
    def populateFields(self):
        """Populate all fields from the loaded configuration"""
        if not self.config:
            return
            
        # Display section
        if 'DISPLAY' in self.config:
            display = self.config['DISPLAY']
            # Basic settings
            self.displayBloom.setChecked(self.getBoolValue(display.get('Bloom', '0')))
            self.displayDisableBlurShader.setChecked(self.getBoolValue(display.get('DisableBlurShader', '1')))
            self.displayDisableFogShader.setChecked(self.getBoolValue(display.get('DisableFogShader', '1')))
            self.displayDisableShadowEngine.setChecked(self.getBoolValue(display.get('DisableShadowEngine', '1')))
            self.displayFOV.setValue(float(display.get('FOV', '0.5')))
            self.displayGammaCorrection.setChecked(self.getBoolValue(display.get('GammaCorrection', '1')))
            self.displayMode.setCurrentIndex(int(display.get('Mode', '0')))
            self.displayNoir.setChecked(self.getBoolValue(display.get('Noir', '0')))
            self.displayResolution.setText(display.get('Resolution', '1280x720@60'))
            
            # RGB colors
            for key, field in self.rgbFields.items():
                if key in display:
                    field.setText(display.get(key, ''))
                    
            # UI Positions
            for key, field in self.uiFields.items():
                if key in display:
                    field.setText(display.get(key, ''))
                   
        # Game section
        if 'GAME' in self.config:
            game = self.config['GAME']
            # Core ability
            self.gameAirHikeCoreAbility.setChecked(self.getBoolValue(game.get('AirHike.CoreAbility', '0')))
            
            # Arcade settings
            self.gameArcade.setChecked(self.getBoolValue(game.get('Arcade', '0')))
            self.gameArcadeMission.setValue(int(game.get('Arcade.Mission', '14')))
            self.gameArcadeMode.setValue(int(game.get('Arcade.Mode', '4')))
            self.gameArcadeAutomatic.setChecked(self.getBoolValue(game.get('Arcade.Automatic', '0')))
            self.gameArcadeCharacter.setValue(int(game.get('Arcade.Character', '0')))
            self.gameArcadeBloodyPalace.setText(game.get('Arcade.BloodyPalace', '0,0'))
            self.gameArcadeEquipment.setText(game.get('Arcade.Equipment', '06050100'))
            self.gameArcadeCostume.setValue(int(game.get('Arcade.Costume', '2')))
            self.gameArcadeHP.setValue(int(game.get('Arcade.HP', '20000')))
            self.gameArcadeMP.setValue(int(game.get('Arcade.MP', '10000')))
            self.gameArcadeStyle.setValue(int(game.get('Arcade.Style', '2')))
            self.gameArcadeRoom.setValue(int(game.get('Arcade.Room', '10')))
            self.gameArcadePosition.setValue(int(game.get('Arcade.Position', '0')))
            
            # Artemis settings
            self.gameArtemisInstantCharge.setChecked(self.getBoolValue(game.get('Artemis.InstantCharge', '0')))
            self.gameArtemisNormalShotMultiLockSwap.setChecked(self.getBoolValue(game.get('Artemis.NormalShotMultiLockSwap', '0')))
            
            # Boss Rush
            self.gameBossRush.setChecked(self.getBoolValue(game.get('BossRush', '0')))
            
            # Devil mobility
            for key, field in self.devilFields.items():
                if key in game:
                    field.setValue(int(game.get(key, '1')))
            
            # Human mobility
            for key, field in self.humanFields.items():
                if key in game:
                    field.setValue(int(game.get(key, '1')))
                    
            # Game modifiers
            self.gameForceEasyAutomaticTwosomeTime.setChecked(self.getBoolValue(game.get('ForceEasyAutomaticTwosomeTime', '0')))
            self.gameHideBeowulf.setChecked(self.getBoolValue(game.get('HideBeowulf', '0')))
            self.gameInfiniteMP.setChecked(self.getBoolValue(game.get('InfiniteMP', '0')))
            self.gameInfiniteRainStorm.setChecked(self.getBoolValue(game.get('InfiniteRainStorm', '0')))
            self.gameInfiniteRoundTrip.setChecked(self.getBoolValue(game.get('InfiniteRoundTrip', '0')))
            self.gameInfiniteSwordPierce.setChecked(self.getBoolValue(game.get('InfiniteSwordPierce', '0')))
            self.gameLowBuffer.setValue(int(game.get('LowBuffer', '6')))
            self.gameMPDeplete.setValue(float(game.get('MP.Deplete', '11')))
            self.gameNoDemonForm.setChecked(self.getBoolValue(game.get('NoDemonForm', '0')))
            self.gameOrbReach.setValue(int(game.get('OrbReach', '300')))
            self.gameRevertDelay.setValue(int(game.get('Revert.Delay', '60')))
            
            # Speed settings
            for key, field in self.speedFields.items():
                if key in game:
                    field.setValue(float(game.get(key, '1.0')))
            
            # Style Switcher
            self.gameStyleSwitcher.setChecked(self.getBoolValue(game.get('StyleSwitcher', '0')))
            self.gameStyleSwitcherCancel.setText(game.get('StyleSwitcher.Cancel', '0x1000'))
            self.gameStyleSwitcherChronoSwords.setChecked(self.getBoolValue(game.get('StyleSwitcher.ChronoSwords', '0')))
            self.gameStyleSwitcherNoDoubleTap.setChecked(self.getBoolValue(game.get('StyleSwitcher.NoDoubleTap', '0')))
            
            # Weapon Switcher
            self.gameWeaponSwitcher.setChecked(self.getBoolValue(game.get('WeaponSwitcher', '0')))
            self.gameWeaponSwitcherDevil.setValue(int(game.get('WeaponSwitcher.Devil', '0')))
            self.gameWeaponSwitcherMelee.setText(game.get('WeaponSwitcher.Melee', '00,01,02,03,04'))
            self.gameWeaponSwitcherRanged.setText(game.get('WeaponSwitcher.Ranged', '05,06,07,08,09'))
            self.gameWeaponSwitcherSword.setValue(int(game.get('WeaponSwitcher.Sword', '1')))
            self.gameWeaponSwitcherTimeout.setValue(float(game.get('WeaponSwitcher.Timeout', '6')))
        
        # Input section
        if 'INPUT' in self.config:
            input_section = self.config['INPUT']
            
            # Input settings
            self.inputDisableLockOnToggle.setChecked(self.getBoolValue(input_section.get('DisableLockOnToggle', '0')))
            self.inputHotkeys.setChecked(self.getBoolValue(input_section.get('Hotkeys', '1')))
            
            # Hotkeys
            for key, field in self.hotkeyFields.items():
                if key in input_section:
                    field.setText(input_section.get(key, ''))
            
            # Keyboard mappings
            for key, field in self.keyboardFields.items():
                if key in input_section:
                    field.setText(input_section.get(key, ''))
        
        # Sound section
        if 'SOUND' in self.config:
            sound = self.config['SOUND']
            
            # Sound settings
            self.soundDisableSoundDriver.setChecked(self.getBoolValue(sound.get('DisableSoundDriver', '0')))
            self.soundDisableStageSE.setChecked(self.getBoolValue(sound.get('DisableStageSE', '0')))
            self.soundDisableSystemSE.setChecked(self.getBoolValue(sound.get('DisableSystemSE', '0')))
            self.soundForceMode0.setChecked(self.getBoolValue(sound.get('ForceMode0', '0')))
            
            # Volume
            self.soundVolumeBGM.setValue(int(sound.get('Volume.BGM', '100')))
            self.soundVolumeSE.setValue(int(sound.get('Volume.SE', '127')))
            # Raw BGM[] data
            if hasattr(self.config, 'bgm_data') and self.config.bgm_data:
                self.bgmTextEdit.setPlainText(self.config.bgm_data)
        
        # System section
        if 'SYSTEM' in self.config:
            system = self.config['SYSTEM']
            
            # System settings
            self.systemHideCursor.setChecked(self.getBoolValue(system.get('HideCursor', '0')))
            self.systemInvertCamera.setChecked(self.getBoolValue(system.get('InvertCamera', '0')))
            self.systemLanguage.setCurrentIndex(int(system.get('Language', '1')))
            self.systemSkipCutscenes.setChecked(self.getBoolValue(system.get('SkipCutscenes', '0')))
            self.systemSkipIntro.setChecked(self.getBoolValue(system.get('SkipIntro', '0')))
            self.systemSubtitles.setCurrentIndex(int(system.get('Subtitles', '1')))
            self.systemSubtitlesEnable.setChecked(self.getBoolValue(system.get('Subtitles.Enable', '0')))
            
    def updateConfigFromFields(self):
        """Update the configuration object from UI fields"""
        if not self.config:
            self.config = StyleSwitcherConfigParser(strict=False)
            # optionxform is set in the class already
        
        # Ensure sections exist
        for section in ['DISPLAY', 'GAME', 'INPUT', 'SOUND', 'SYSTEM']:
            if section not in self.config:
                self.config[section] = {}
        
        # Display section
        display = self.config['DISPLAY']
        display['Bloom'] = str(int(self.displayBloom.isChecked()))
        display['DisableBlurShader'] = str(int(self.displayDisableBlurShader.isChecked()))
        display['DisableFogShader'] = str(int(self.displayDisableFogShader.isChecked()))
        display['DisableShadowEngine'] = str(int(self.displayDisableShadowEngine.isChecked()))
        display['FOV'] = str(self.displayFOV.value())
        display['GammaCorrection'] = str(int(self.displayGammaCorrection.isChecked()))
        display['Mode'] = str(self.displayMode.currentIndex())
        display['Noir'] = str(int(self.displayNoir.isChecked()))
        display['Resolution'] = self.displayResolution.text()
        
        # RGB Colors
        for key, field in self.rgbFields.items():
            if field.text():
                display[key] = field.text()
                
        # UI Positions
        for key, field in self.uiFields.items():
            if field.text():
                display[key] = field.text()
        
        # Game section
        game = self.config['GAME']
        game['AirHike.CoreAbility'] = str(int(self.gameAirHikeCoreAbility.isChecked()))
        
        # Arcade settings
        game['Arcade'] = str(int(self.gameArcade.isChecked()))
        game['Arcade.Mission'] = str(self.gameArcadeMission.value())
        game['Arcade.Mode'] = str(self.gameArcadeMode.value())
        game['Arcade.Automatic'] = str(int(self.gameArcadeAutomatic.isChecked()))
        game['Arcade.Character'] = str(self.gameArcadeCharacter.value())
        game['Arcade.BloodyPalace'] = self.gameArcadeBloodyPalace.text()
        game['Arcade.Equipment'] = self.gameArcadeEquipment.text()
        game['Arcade.Costume'] = str(self.gameArcadeCostume.value())
        game['Arcade.HP'] = str(self.gameArcadeHP.value())
        game['Arcade.MP'] = str(self.gameArcadeMP.value())
        game['Arcade.Style'] = str(self.gameArcadeStyle.value())
        game['Arcade.Room'] = str(self.gameArcadeRoom.value())
        game['Arcade.Position'] = str(self.gameArcadePosition.value())
        
        # Artemis settings
        game['Artemis.InstantCharge'] = str(int(self.gameArtemisInstantCharge.isChecked()))
        game['Artemis.NormalShotMultiLockSwap'] = str(int(self.gameArtemisNormalShotMultiLockSwap.isChecked()))
        
        # Boss Rush
        game['BossRush'] = str(int(self.gameBossRush.isChecked()))
        
        # Devil mobility
        for key, field in self.devilFields.items():
            game[key] = str(field.value())
            
        # Human mobility
        for key, field in self.humanFields.items():
            game[key] = str(field.value())
            
        # Game modifiers
        game['ForceEasyAutomaticTwosomeTime'] = str(int(self.gameForceEasyAutomaticTwosomeTime.isChecked()))
        game['HideBeowulf'] = str(int(self.gameHideBeowulf.isChecked()))
        game['InfiniteMP'] = str(int(self.gameInfiniteMP.isChecked()))
        game['InfiniteRainStorm'] = str(int(self.gameInfiniteRainStorm.isChecked()))
        game['InfiniteRoundTrip'] = str(int(self.gameInfiniteRoundTrip.isChecked()))
        game['InfiniteSwordPierce'] = str(int(self.gameInfiniteSwordPierce.isChecked()))
        game['LowBuffer'] = str(self.gameLowBuffer.value())
        game['MP.Deplete'] = str(self.gameMPDeplete.value())
        game['NoDemonForm'] = str(int(self.gameNoDemonForm.isChecked()))
        game['OrbReach'] = str(self.gameOrbReach.value())
        game['Revert.Delay'] = str(self.gameRevertDelay.value())
        
        # Speed settings
        for key, field in self.speedFields.items():
            game[key] = str(field.value())
            
        # Style Switcher
        game['StyleSwitcher'] = str(int(self.gameStyleSwitcher.isChecked()))
        game['StyleSwitcher.Cancel'] = self.gameStyleSwitcherCancel.text()
        game['StyleSwitcher.ChronoSwords'] = str(int(self.gameStyleSwitcherChronoSwords.isChecked()))
        game['StyleSwitcher.NoDoubleTap'] = str(int(self.gameStyleSwitcherNoDoubleTap.isChecked()))
        
        # Weapon Switcher
        game['WeaponSwitcher'] = str(int(self.gameWeaponSwitcher.isChecked()))
        game['WeaponSwitcher.Devil'] = str(self.gameWeaponSwitcherDevil.value())
        game['WeaponSwitcher.Melee'] = self.gameWeaponSwitcherMelee.text()
        game['WeaponSwitcher.Ranged'] = self.gameWeaponSwitcherRanged.text()
        game['WeaponSwitcher.Sword'] = str(self.gameWeaponSwitcherSword.value())
        game['WeaponSwitcher.Timeout'] = str(self.gameWeaponSwitcherTimeout.value())
        
        # Input section
        input_section = self.config['INPUT']
        input_section['DisableLockOnToggle'] = str(int(self.inputDisableLockOnToggle.isChecked()))
        input_section['Hotkeys'] = str(int(self.inputHotkeys.isChecked()))
        
        # Hotkeys
        for key, field in self.hotkeyFields.items():
            if field.text():
                input_section[key] = field.text()
                
        # Keyboard mappings
        for key, field in self.keyboardFields.items():
            if field.text():
                input_section[key] = field.text()
                
        # Sound section
        sound = self.config['SOUND']
        sound['DisableSoundDriver'] = str(int(self.soundDisableSoundDriver.isChecked()))
        sound['DisableStageSE'] = str(int(self.soundDisableStageSE.isChecked()))
        sound['DisableSystemSE'] = str(int(self.soundDisableSystemSE.isChecked()))
        sound['ForceMode0'] = str(int(self.soundForceMode0.isChecked()))
        sound['Volume.BGM'] = str(self.soundVolumeBGM.value())
        sound['Volume.SE'] = str(self.soundVolumeSE.value())
        # Capture raw BGM[] data from editable text area
        raw_bgm = self.bgmTextEdit.toPlainText().strip()
        self.config.bgm_data = raw_bgm
        
        # System section
        system = self.config['SYSTEM']
        system['HideCursor'] = str(int(self.systemHideCursor.isChecked()))
        system['InvertCamera'] = str(int(self.systemInvertCamera.isChecked()))
        system['Language'] = str(self.systemLanguage.currentIndex())
        system['SkipCutscenes'] = str(int(self.systemSkipCutscenes.isChecked()))
        system['SkipIntro'] = str(int(self.systemSkipIntro.isChecked()))
        system['Subtitles'] = str(self.systemSubtitles.currentIndex())
        system['Subtitles.Enable'] = str(int(self.systemSubtitlesEnable.isChecked()))
        
    def getBoolValue(self, value):
        """Convert string values to boolean"""
        if isinstance(value, str):
            return value.lower() in ('1', 'true', 'yes', 'on')
        return bool(value)


def main():
    app = QApplication(sys.argv)
    ui = StyleSwitcherUI(app)
    ui.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
