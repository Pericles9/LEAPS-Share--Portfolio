"""Strategy package for options-based portfolio construction."""

from .options_strategy_engine import (
    OptionsStrategyEngine,
    OptionsFactors,
    OptionsSurface,
    StrategyConfig,
    STRATEGY_CONFIGS
)

__all__ = [
    'OptionsStrategyEngine',
    'OptionsFactors', 
    'OptionsSurface',
    'StrategyConfig',
    'STRATEGY_CONFIGS'
]