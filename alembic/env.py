# Import settings
import sys
from logging.config import fileConfig
from pathlib import Path

from geoalchemy2 import alembic_helpers
from sqlalchemy import engine_from_config, pool

from alembic import context

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings

# Import all models so Alembic can detect them
# Импорт необходим, чтобы классы загрузились и зарегистрировались в Base.metadata
from app.db import models  # noqa: F401 - импорт для side-effect
from app.db.base import Base

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Override sqlalchemy.url with our settings
config.set_main_option("sqlalchemy.url", settings.database_url_sync)

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata


def include_object(object, name, type_, reflected, compare_to):
    """
    Игнорируем служебные таблицы PostGIS при autogenerate.
    """
    if type_ == "table" and name in {
        # PostGIS Tiger Geocoder tables
        'addr', 'addrfeat', 'bg', 'county', 'county_lookup', 'countysub_lookup',
        'cousub', 'direction_lookup', 'edges', 'faces', 'featnames',
        'geocode_settings', 'geocode_settings_default', 'layer', 'loader_lookuptables',
        'loader_platform', 'loader_variables', 'pagc_gaz', 'pagc_lex', 'pagc_rules',
        'place', 'place_lookup', 'secondary_unit_lookup', 'state', 'state_lookup',
        'street_type_lookup', 'tabblock', 'tabblock20', 'topology', 'tract',
        'zcta5', 'zip_lookup', 'zip_lookup_all', 'zip_lookup_base', 'zip_state',
        'zip_state_loc'
    }:
        return False
    return alembic_helpers.include_object(object, name, type_, reflected, compare_to)

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        # PostGIS support + ignore tiger geocoder tables
        include_object=include_object,
        process_revision_directives=alembic_helpers.writer,
        render_item=alembic_helpers.render_item,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            # PostGIS support + ignore tiger geocoder tables
            include_object=include_object,
            process_revision_directives=alembic_helpers.writer,
            render_item=alembic_helpers.render_item,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
