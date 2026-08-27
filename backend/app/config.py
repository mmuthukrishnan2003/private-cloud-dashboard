from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "Private Cloud Dashboard"
    APP_VERSION: str = "1.0.0"

    # Main KVM server
    HOST_NAME: str = "demo"
    HOST_IP: str = "172.16.0.111"

    # libvirt / KVM
    LIBVIRT_URI: str = "qemu:///system"

    # Default VM storage
    VM_STORAGE_PATH: str = "/var/lib/libvirt/images"

    # API
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
