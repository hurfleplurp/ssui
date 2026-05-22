#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
import configparser
import re
from PyQt5.QtWidgets import (QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout, 
                            QHBoxLayout, QLabel, QLineEdit, QSpinBox, QDoubleSpinBox, 
                            QComboBox, QCheckBox, QPushButton, QFileDialog, QMessageBox,
                            QScrollArea, QGridLayout, QGroupBox, QFormLayout)
from PyQt5.QtCore import Qt, QSettings
from PyQt5.QtGui import QColor, QIcon


class StyleSwitcherConfigParser(configparser.ConfigParser):
    """Extend ConfigParser to handle StyleSwitcher's BGM array format"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bgm_data = None
        # Need to set optionxform using this approach for ConfigParser
        self._optionxform = str  # Preserve case sensitivity
        
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
    def __init__(self):
        super().__init__()
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
        """Helper to create a scrollable group with form layout"""
        groupBox = QGroupBox(title)
        scrollArea = QScrollArea()
        scrollArea.setWidgetResizable(True)
        scrollContent = QWidget()
        layout = QFormLayout(scrollContent)
        scrollArea.setWidget(scrollContent)
        
        groupLayout = QVBoxLayout(groupBox)
        groupLayout.addWidget(scrollArea)
        
        return groupBox, layout

    def createDisplayTab(self):
        # Display Tab
        displayTab = QWidget()
        displayLayout = QVBoxLayout(displayTab)
        
        # General display settings
        generalGroup, generalLayout = self.createScrollableGroupLayout("General Display Settings")
        
        # Create fields for each setting based on documentation
        self.displayBloom = QCheckBox("Enable Bloom")
        self.displayBloom.setToolTip("Looks great in most rooms, looks horrible in some rooms.\nYou can toggle it ingame by pressing F5.")
        generalLayout.addRow("Bloom:", self.displayBloom)
        
        self.displayDisableBlurShader = QCheckBox("Disable Blur Shader")
        generalLayout.addRow("Disable Blur Shader:", self.displayDisableBlurShader)
        
        self.displayDisableFogShader = QCheckBox("Disable Fog Shader")
        generalLayout.addRow("Disable Fog Shader:", self.displayDisableFogShader)
        
        self.displayDisableShadowEngine = QCheckBox("Disable Shadow Engine")
        generalLayout.addRow("Disable Shadow Engine:", self.displayDisableShadowEngine)
        
        self.displayFOV = QDoubleSpinBox()
        self.displayFOV.setRange(0.1, 2.0)
        self.displayFOV.setSingleStep(0.1)
        self.displayFOV.setToolTip("Sets the field of view")
        generalLayout.addRow("Field of View:", self.displayFOV)
        
        self.displayGammaCorrection = QCheckBox("Enable Gamma Correction")
        generalLayout.addRow("Gamma Correction:", self.displayGammaCorrection)
        
        self.displayMode = QComboBox()
        self.displayMode.addItems(["Windowed", "Fullscreen"])
        generalLayout.addRow("Display Mode:", self.displayMode)
        
        self.displayNoir = QCheckBox("Enable Noir Mode")
        self.displayNoir.setToolTip("Turns models black while keeping most of their effects intact.\nYou can toggle it ingame by pressing F6.")
        generalLayout.addRow("Noir Mode:", self.displayNoir)
        
        self.displayResolution = QLineEdit()
        self.displayResolution.setPlaceholderText("WidthxHeight@FPS (e.g. 1280x720@60)")
        generalLayout.addRow("Resolution:", self.displayResolution)
        
        displayLayout.addWidget(generalGroup)
        
        # RGB Color settings
        rgbGroup, rgbLayout = self.createScrollableGroupLayout("RGB Color Settings")
        
        # Create RGB color fields
        self.rgbFields = {}
        rgb_colors = [
            "RGB.Rebellion", "RGB.Cerberus", "RGB.AgniRudra", "RGB.Nevan", "RGB.Beowulf",
            "RGB.Sparda", "RGB.Yamato", "RGB.Beowulf.Vergil", "RGB.ForceEdge", "RGB.NeroAngelo",
            "RGB.AirHike.Rebellion", "RGB.AirHike.Cerberus", "RGB.AirHike.AgniRudra",
            "RGB.AirHike.Nevan", "RGB.AirHike.Beowulf", "RGB.SkyStar", "RGB.Ultimate"
        ]
        
        for color in rgb_colors:
            self.rgbFields[color] = QLineEdit()
            self.rgbFields[color].setPlaceholderText("RRGGBB (hex)")
            rgbLayout.addRow(f"{color}:", self.rgbFields[color])
            
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
        # Game Tab
        gameTab = QWidget()
        gameLayout = QVBoxLayout(gameTab)
        
        # Core abilities group
        coreGroup, coreLayout = self.createScrollableGroupLayout("Core Abilities")
        
        self.gameAirHikeCoreAbility = QCheckBox("Air Hike Core Ability")
        self.gameAirHikeCoreAbility.setToolTip("When checked, Air Hike is available without purchasing")
        coreLayout.addRow("Air Hike Core Ability:", self.gameAirHikeCoreAbility)
        
        gameLayout.addWidget(coreGroup)
        
        # Arcade Mode group
        arcadeGroup, arcadeLayout = self.createScrollableGroupLayout("Arcade Mode")
        
        self.gameArcade = QCheckBox("Enable Arcade Mode")
        arcadeLayout.addRow("Arcade Mode:", self.gameArcade)
        
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
        artemisLayout.addRow("Instant Charge:", self.gameArtemisInstantCharge)
        
        self.gameArtemisNormalShotMultiLockSwap = QCheckBox("Normal Shot/Multi-Lock Swap")
        artemisLayout.addRow("Normal Shot/Multi-Lock Swap:", self.gameArtemisNormalShotMultiLockSwap)
        
        gameLayout.addWidget(artemisGroup)
        
        # Boss Rush group
        bossGroup, bossLayout = self.createScrollableGroupLayout("Boss Rush")
        
        self.gameBossRush = QCheckBox("Enable Boss Rush")
        self.gameBossRush.setToolTip("Enables the boss rush mode")
        bossLayout.addRow("Boss Rush:", self.gameBossRush)
        
        gameLayout.addWidget(bossGroup)
        
        # Devil Mobility group
        devilGroup, devilLayout = self.createScrollableGroupLayout("Devil Mobility")
        
        self.devilFields = {}
        devil_settings = [
            "Devil.Walk", "Devil.Dash", "Devil.Run", "Devil.Jump.Height", "Devil.Jump.Forward",
            "Devil.AirHike.Height", "Devil.AirHike.Forward", "Devil.Fall", "Devil.Roll.Forward"
        ]
        
        for setting in devil_settings:
            self.devilFields[setting] = QSpinBox()
            self.devilFields[setting].setRange(1, 10)
            devilLayout.addRow(f"{setting}:", self.devilFields[setting])
            
        gameLayout.addWidget(devilGroup)
        
        # Human Mobility group
        humanGroup, humanLayout = self.createScrollableGroupLayout("Human Mobility")
        
        self.humanFields = {}
        human_settings = [
            "Human.Walk", "Human.Dash", "Human.Run", "Human.Jump.Height", "Human.Jump.Forward",
            "Human.AirHike.Height", "Human.AirHike.Forward", "Human.Fall", "Human.Roll.Forward"
        ]
        
        for setting in human_settings:
            self.humanFields[setting] = QSpinBox()
            self.humanFields[setting].setRange(1, 10)
            humanLayout.addRow(f"{setting}:", self.humanFields[setting])
            
        gameLayout.addWidget(humanGroup)
        
        # Game Modifiers group
        modifiersGroup, modifiersLayout = self.createScrollableGroupLayout("Game Modifiers")
        
        self.gameForceEasyAutomaticTwosomeTime = QCheckBox("Force Easy Automatic Twosome Time")
        modifiersLayout.addRow("Force Easy Automatic Twosome Time:", self.gameForceEasyAutomaticTwosomeTime)
        
        self.gameHideBeowulf = QCheckBox("Hide Beowulf")
        modifiersLayout.addRow("Hide Beowulf:", self.gameHideBeowulf)
        
        self.gameInfiniteMP = QCheckBox("Infinite MP")
        modifiersLayout.addRow("Infinite MP:", self.gameInfiniteMP)
        
        self.gameInfiniteRainStorm = QCheckBox("Infinite Rain Storm")
        modifiersLayout.addRow("Infinite Rain Storm:", self.gameInfiniteRainStorm)
        
        self.gameInfiniteRoundTrip = QCheckBox("Infinite Round Trip")
        modifiersLayout.addRow("Infinite Round Trip:", self.gameInfiniteRoundTrip)
        
        self.gameInfiniteSwordPierce = QCheckBox("Infinite Sword Pierce")
        modifiersLayout.addRow("Infinite Sword Pierce:", self.gameInfiniteSwordPierce)
        
        self.gameLowBuffer = QSpinBox()
        self.gameLowBuffer.setRange(1, 20)
        modifiersLayout.addRow("Low Buffer:", self.gameLowBuffer)
        
        self.gameMPDeplete = QDoubleSpinBox()
        self.gameMPDeplete.setRange(0, 100)
        self.gameMPDeplete.setSingleStep(1)
        modifiersLayout.addRow("MP Deplete:", self.gameMPDeplete)
        
        self.gameNoDemonForm = QCheckBox("No Demon Form")
        modifiersLayout.addRow("No Demon Form:", self.gameNoDemonForm)
        
        self.gameOrbReach = QSpinBox()
        self.gameOrbReach.setRange(10, 1000)
        self.gameOrbReach.setSingleStep(10)
        modifiersLayout.addRow("Orb Reach:", self.gameOrbReach)
        
        self.gameRevertDelay = QSpinBox()
        self.gameRevertDelay.setRange(0, 200)
        modifiersLayout.addRow("Revert Delay:", self.gameRevertDelay)
        
        gameLayout.addWidget(modifiersGroup)
        
        # Speed Settings group
        speedGroup, speedLayout = self.createScrollableGroupLayout("Speed Settings")
        
        self.speedFields = {}
        speed_settings = [
            "Speed.AirHike", "Speed.Backward", "Speed.BackwardDash", "Speed.DarkSlayer",
            "Speed.Dash", "Speed.DevilTrigger", "Speed.GunStinger", "Speed.Jump",
            "Speed.NeroAngelo", "Speed.Run", "Speed.SkyDance", "Speed.SkyDance.Slam",
            "Speed.Stinger", "Speed.Walk"
        ]
        
        for setting in speed_settings:
            self.speedFields[setting] = QDoubleSpinBox()
            self.speedFields[setting].setRange(0.1, 10.0)
            self.speedFields[setting].setSingleStep(0.1)
            self.speedFields[setting].setValue(1.0)
            speedLayout.addRow(f"{setting}:", self.speedFields[setting])
            
        gameLayout.addWidget(speedGroup)
        
        # Style Switcher group
        styleGroup, styleLayout = self.createScrollableGroupLayout("Style Switcher")
        
        self.gameStyleSwitcher = QCheckBox("Enable Style Switcher")
        styleLayout.addRow("Style Switcher:", self.gameStyleSwitcher)
        
        self.gameStyleSwitcherCancel = QLineEdit()
        self.gameStyleSwitcherCancel.setPlaceholderText("0x1000")
        styleLayout.addRow("Cancel:", self.gameStyleSwitcherCancel)
        
        self.gameStyleSwitcherChronoSwords = QCheckBox("Chrono Swords")
        styleLayout.addRow("Chrono Swords:", self.gameStyleSwitcherChronoSwords)
        
        self.gameStyleSwitcherNoDoubleTap = QCheckBox("No Double Tap")
        styleLayout.addRow("No Double Tap:", self.gameStyleSwitcherNoDoubleTap)
        
        gameLayout.addWidget(styleGroup)
        
        # Weapon Switcher group
        weaponGroup, weaponLayout = self.createScrollableGroupLayout("Weapon Switcher")
        
        self.gameWeaponSwitcher = QCheckBox("Enable Weapon Switcher")
        weaponLayout.addRow("Weapon Switcher:", self.gameWeaponSwitcher)
        
        self.gameWeaponSwitcherDevil = QSpinBox()
        self.gameWeaponSwitcherDevil.setRange(0, 10)
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
        # Input Tab
        inputTab = QWidget()
        inputLayout = QVBoxLayout(inputTab)
        
        # Input Settings Group
        inputGroup, inputGroupLayout = self.createScrollableGroupLayout("Input Settings")
        
        self.inputDisableLockOnToggle = QCheckBox("Disable Lock-On Toggle")
        inputGroupLayout.addRow("Disable Lock-On Toggle:", self.inputDisableLockOnToggle)
        
        self.inputHotkeys = QCheckBox("Enable Hotkeys")
        inputGroupLayout.addRow("Hotkeys:", self.inputHotkeys)
        
        inputLayout.addWidget(inputGroup)
        
        # Hotkey Settings Group
        hotkeyGroup, hotkeyLayout = self.createScrollableGroupLayout("Hotkey Settings")
        
        self.hotkeyFields = {}
        hotkeys = [
            "Hotkey.NeroAngelo", "Hotkey.DSNeroAngelo", "Hotkey.QuickDT", 
            "Hotkey.Trickster", "Hotkey.Swordmaster", "Hotkey.Gunslinger", "Hotkey.Royalguard",
            "Hotkey.QuickStyle.Trickster", "Hotkey.QuickStyle.Swordmaster",
            "Hotkey.QuickStyle.Gunslinger", "Hotkey.QuickStyle.Royalguard",
            "Hotkey.PositionSaver", "Hotkey.PositionLoader", "Hotkey.Bail"
        ]
        
        for key in hotkeys:
            self.hotkeyFields[key] = QLineEdit()
            self.hotkeyFields[key].setPlaceholderText("Keyboard key code")
            hotkeyLayout.addRow(f"{key}:", self.hotkeyFields[key])
            
        inputLayout.addWidget(hotkeyGroup)
        
        # Keyboard Settings Group
        keyboardGroup, keyboardLayout = self.createScrollableGroupLayout("Keyboard Settings")
        
        self.keyboardFields = {}
        keyboard_keys = [
            "Keyboard.Forward", "Keyboard.Backward", "Keyboard.Left", "Keyboard.Right",
            "Keyboard.Lock", "Keyboard.Melee", "Keyboard.Gun", "Keyboard.Style",
            "Keyboard.Switch.Melee", "Keyboard.Switch.Gun", "Keyboard.DT", "Keyboard.Jump",
            "Keyboard.Map", "Keyboard.PauseMenu", "Keyboard.MissionStart"
        ]
        
        for key in keyboard_keys:
            self.keyboardFields[key] = QLineEdit()
            self.keyboardFields[key].setPlaceholderText("Keyboard key code")
            keyboardLayout.addRow(f"{key}:", self.keyboardFields[key])
            
        inputLayout.addWidget(keyboardGroup)
        
        # Add tab to tabwidget
        self.tabs.addTab(inputTab, "Input")

    def createSoundTab(self):
        # Sound Tab
        soundTab = QWidget()
        soundLayout = QVBoxLayout(soundTab)
        
        # Sound Settings Group
        soundGroup, soundGroupLayout = self.createScrollableGroupLayout("Sound Settings")
        
        # Sound settings
        self.soundDisableSoundDriver = QCheckBox("Disable Sound Driver")
        self.soundDisableSoundDriver.setToolTip("Disable the sound driver entirely, removing BGM engine related fps drops")
        soundGroupLayout.addRow("Disable Sound Driver:", self.soundDisableSoundDriver)
        
        self.soundDisableStageSE = QCheckBox("Disable Stage Sound Effects")
        soundGroupLayout.addRow("Disable Stage Sound Effects:", self.soundDisableStageSE)
        
        self.soundDisableSystemSE = QCheckBox("Disable System Sound Effects")
        soundGroupLayout.addRow("Disable System Sound Effects:", self.soundDisableSystemSE)
        
        self.soundForceMode0 = QCheckBox("Force Mode 0")
        self.soundForceMode0.setToolTip("Use sound playback mode 0 which has fewer FPS drops")
        soundGroupLayout.addRow("Force Mode 0:", self.soundForceMode0)
        
        # Volume settings
        self.soundVolumeBGM = QSpinBox()
        self.soundVolumeBGM.setRange(0, 100)
        soundGroupLayout.addRow("BGM Volume:", self.soundVolumeBGM)
        
        self.soundVolumeSE = QSpinBox()
        self.soundVolumeSE.setRange(0, 127)
        soundGroupLayout.addRow("SE Volume:", self.soundVolumeSE)
        
        soundLayout.addWidget(soundGroup)
        
        # BGM Settings Group
        bgmGroup = QGroupBox("BGM Settings")
        bgmLayout = QVBoxLayout(bgmGroup)
        bgmLabel = QLabel("BGM settings are complex and not editable in this UI version.\nPlease modify these directly in the config file.")
        bgmLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        bgmLayout.addWidget(bgmLabel)
        
        soundLayout.addWidget(bgmGroup)
        
        # Add tab to tabwidget
        self.tabs.addTab(soundTab, "Sound")

    def createSystemTab(self):
        # System Tab
        systemTab = QWidget()
        systemLayout = QVBoxLayout(systemTab)
        
        # System Settings Group
        systemGroup, systemGroupLayout = self.createScrollableGroupLayout("System Settings")
        
        self.systemHideCursor = QCheckBox("Hide Cursor")
        systemGroupLayout.addRow("Hide Cursor:", self.systemHideCursor)
        
        self.systemInvertCamera = QCheckBox("Invert Camera")
        systemGroupLayout.addRow("Invert Camera:", self.systemInvertCamera)
        
        self.systemLanguage = QComboBox()
        self.systemLanguage.addItems(["English", "Japanese"])
        systemGroupLayout.addRow("Language:", self.systemLanguage)
        
        self.systemSkipCutscenes = QCheckBox("Skip Cutscenes")
        systemGroupLayout.addRow("Skip Cutscenes:", self.systemSkipCutscenes)
        
        self.systemSkipIntro = QCheckBox("Skip Intro")
        systemGroupLayout.addRow("Skip Intro:", self.systemSkipIntro)
        
        self.systemSubtitles = QComboBox()
        self.systemSubtitles.addItems(["None", "English", "French", "German", "Italian", "Spanish", "Japanese"])
        systemGroupLayout.addRow("Subtitles:", self.systemSubtitles)
        
        self.systemSubtitlesEnable = QCheckBox("Enable Subtitles")
        systemGroupLayout.addRow("Enable Subtitles:", self.systemSubtitlesEnable)
        
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
            QMessageBox.critical(self, "Error", f"Failed to load configuration: {str(e)}")    def saveConfig(self):
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
    ui = StyleSwitcherUI()
    ui.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
