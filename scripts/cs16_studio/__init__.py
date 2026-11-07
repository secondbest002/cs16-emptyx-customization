"""
CS 1.6 EmptyX Customization Suite - Asset Studio & Mod Hub Pro.
"""

__version__ = "2.1.0"

from .config_manager import config
from .color_adjuster import adjust_color_grading, adjust_and_quantize
from .glove_transfer import transfer_gloves, batch_transfer_gloves
from .image_pipeline import process_slot_sticker_with_transform
from .mdl_core import MdlModel, extract_model_3d
from .pw_restore import (
    find_model_backup,
    restore_single_model_file,
    resolve_weapon_triplet,
    restore_weapon_models,
)
from .stattrak_customizer import customize_stattrak_texture
from .wear_simulator import apply_wear_simulation, simulate_and_quantize
from .sticker_scraper import apply_sticker_scraping, generate_scrape_mask, get_scrape_condition_name, scrape_and_quantize
from .modpack_exporter import export_modpack
from .slot_geometry import reposition_slot_quad, inject_new_slot_quad, validate_model_health
from .chrome_injector import (
    inspect_chrome_status,
    inject_chrome_overlay,
    remove_chrome_overlay,
    generate_chrome_texture,
)
from .pov_manager import (
    PovConfig,
    PRESETS,
    get_preset,
    validate_and_clamp,
    export_cfg_string,
    parse_cfg_string,
    apply_to_game,
    reset_to_vanilla,
    read_current_config,
)
from .inventory_manager import (
    save_to_inventory,
    list_inventory,
    equip_inventory_skin,
    sync_gloves_to_inventory,
    delete_inventory_skin,
    toggle_amxx_registration,
)
