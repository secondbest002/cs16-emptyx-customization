"""
tools/cs16_mod_hub/core/__init__.py
Core backend adapters and utilities for CS 1.6 Mod Hub.
"""

from .common import AdapterResult, get_project_root, run_script_streaming
from .model_adapter import (
    transfer_skin,
    inject_gloves,
    inject_pw,
    list_viewmodels,
    list_donor_models,
    list_backups,
    restore_model_backup,
    restore_all_backups,
    verify_goldsrc_mdl_header,
)
from .vibrance_adapter import (
    apply_vibrance,
    reset_vibrance,
    get_preset_values,
    list_presets,
    list_target_groups,
    has_palette_backup,
)
from .sticker_adapter import (
    set_sticker_fx,
    scan_model_stickers,
    list_supported_modes,
    get_mode_description,
)
from .palette_preview import (
    adjust_rgb,
    transform_palette,
    extract_weapon_texture,
    list_model_textures,
    generate_preview_images,
    TexturePreviewCache,
)
from .amxx_adapter import (
    AmxxAdapter,
    PluginInfo,
    CompetitiveSetting,
    get_plugin_status,
    set_plugin_status,
    list_custom_plugins,
    list_all_plugins,
    get_cvar,
    set_cvar,
    get_competitive_settings,
    set_competitive_settings,
    get_cs2_engine_settings,
    set_cs2_engine_cvar,
    set_cs2_engine_settings,
)
from .bot_adapter import (
    BotAdapter,
    get_bot_adapter,
)
