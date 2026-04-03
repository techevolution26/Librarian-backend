from typing import Literal

from pydantic import BaseModel, ConfigDict

ThemeOption = Literal["system", "light", "dark"]
DensityOption = Literal["comfortable", "compact"]
ReadingModeOption = Literal["paged", "scroll"]
FontSizeOption = Literal["small", "medium", "large"]
LineHeightOption = Literal["compact", "comfortable", "relaxed"]
VisibilityOption = Literal["private", "friends", "public"]


class AccountSettingsRead(BaseModel):
    full_name: str
    email: str
    plan: str


class AppearanceSettingsRead(BaseModel):
    theme: ThemeOption | str
    density: DensityOption | str
    reading_mode: ReadingModeOption | str


class ReadingSettingsRead(BaseModel):
    font_size: FontSizeOption | str
    line_height: LineHeightOption | str
    auto_bookmark: bool
    show_progress_bar: bool


class NotificationSettingsRead(BaseModel):
    email_updates: bool
    reading_reminders: bool
    product_announcements: bool


class PrivacySettingsRead(BaseModel):
    profile_visibility: VisibilityOption | str
    share_reading_activity: bool


class UserSettingsRead(BaseModel):
    account: AccountSettingsRead
    appearance: AppearanceSettingsRead
    reading: ReadingSettingsRead
    notifications: NotificationSettingsRead
    privacy: PrivacySettingsRead


class UserSettingsUpdate(BaseModel):
    theme: ThemeOption | None = None
    density: DensityOption | None = None
    reading_mode: ReadingModeOption | None = None
    font_size: FontSizeOption | None = None
    line_height: LineHeightOption | None = None
    auto_bookmark: bool | None = None
    show_progress_bar: bool | None = None
    email_updates: bool | None = None
    reading_reminders: bool | None = None
    product_announcements: bool | None = None
    profile_visibility: VisibilityOption | None = None
    share_reading_activity: bool | None = None

    model_config = ConfigDict(extra="forbid")