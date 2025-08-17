"""Centralized user-facing texts for the Telegram bot.

All texts are English-only to keep the product consistent and easy to
internationalize in the future.
"""

from typing import Final


WELCOME_NEW_USER_TEXT: Final[str] = (
    "🚀 <b>Welcome to PingBrief</b>\n\n"
    "Get concise daily news summaries — <b>in your chosen language</b> — from top sources, in one place.\n\n"
    "• Pick sources below\n"
    "• Tap <b>Continue</b>\n"
    "• Choose your language on the next step"
)


WELCOME_EXISTING_USER_TEXT: Final[str] = (
    "🎉 <b>Welcome back</b>\n\n"
    "You will receive concise daily summaries <b>in your chosen language</b> from:\n\n"
    "{sources}\n\n"
    "Active sources: <b>{count}</b>. Manage them below."
)


HELP_TEXT: Final[str] = (
    "🤖 <b>PingBrief</b>\n\n"
    "Choose sources → pick a language → receive concise digests.\n\n"
    "Commands:\n"
    "• <code>/start</code> — start or pick sources\n"
    "• <code>/settings</code> — manage sources and language\n"
    "• <code>/premium</code> — premium status and purchase"
)
LOADING_PREPARE_LANG_TEXT: Final[str] = "⏳ Preparing language options..."
LOADING_APPLY_CHANGES_TEXT: Final[str] = "⏳ Applying changes..."
LOADING_SAVING_PREFS_TEXT: Final[str] = "⏳ Saving your preferences..."

PREMIUM_ACTIVE_TEXT: Final[str] = "✅ Premium is active until: <b>{until}</b>"
PREMIUM_INACTIVE_TEXT: Final[str] = (
    "❌ Premium is not active.\n\nTap the button below to purchase."
)


UNKNOWN_COMMAND_TEXT: Final[str] = (
    "❓ <b>Unknown command</b>\n\n"
    "I don't recognize that command. Here are the available commands:\n\n"
    "• <code>/start</code> - Start the bot\n"
    "• <code>/settings</code> - Manage subscriptions\n"
    "• <code>/help</code> - Show help\n\n"
    "💡 Click the buttons below to execute commands:"
)


PAYWALL_MULTIPLE_SOURCES_TEXT: Final[str] = (
    "⭐ <b>Premium required</b>\n\n"
    "Free plan allows <b>1 source</b>.\n\n"
    "To use multiple sources, please purchase Premium.\n\n"
    "Choose an option below:"
)


NO_SUBSCRIPTIONS_TEXT: Final[str] = (
    "📭 <b>No subscriptions found</b>\n\n"
    "You don't have any subscriptions yet.\n"
    "Click the button below to create your first subscription!"
)


NO_ACTIVE_SUBSCRIPTIONS_TEXT: Final[str] = (
    "📭 <b>No active subscriptions</b>\n\n"
    "You don't have active subscriptions.\n"
    "Click the button below to create a new subscription!"
)


SETTINGS_HEADER_TEXT: Final[str] = (
    "⚙️ <b>Settings</b>\n\n"
    "Active sources: <b>{count}</b>\n\n"
    "{sources}\n\n"
    "Choose an action:"
)


ADD_SUBSCRIPTION_HEADER_TEXT: Final[str] = (
    "📰 <b>Add sources</b>\n\n"
    "Select one or more sources, then tap “Continue”."
)


SELECTED_SOURCES_TEXT: Final[str] = (
    "📰 <b>Selected sources</b>\n\n"
    "You picked <b>{count}</b>:\n\n"
    "{sources}\n\n"
    "🌍 Choose your language:"
)


SUBSCRIPTION_CREATED_TEXT: Final[str] = (
    "🎉 <b>All set</b>\n\n"
    "Sources:\n{sources}\n\n"
    "Language: {flag} {language}"
)


REMOVED_SUBSCRIPTION_TEXT: Final[str] = (
    "🗑️ <b>Subscription removed</b>\n\n"
    "You can add sources again."
)


SUBSCRIPTION_UPDATED_TEXT: Final[str] = (
    "✅ <b>Updated</b>\n\n"
    "Sources:\n{sources}\n\n"
    "Language: {flag} {language}"
)


START_FLOW_HEADER_TEXT: Final[str] = WELCOME_NEW_USER_TEXT

# Additional UI messages
SELECT_AT_LEAST_ONE_SOURCE_TEXT: Final[str] = (
    "⚠️ Please select at least one news source to continue"
)

CHANGE_SOURCES_HEADER_TEXT: Final[str] = (
    "📰 <b>Change Sources</b>\n\nSelect one or more sources:"
)

CHANGE_LANGUAGE_HEADER_TEXT: Final[str] = (
    "🌍 <b>Change Language</b>\n\nSelect your preferred language:"
)

SELECT_SOURCES_HEADER_TEXT: Final[str] = (
    "📰 <b>Select Sources</b>\n\nTap to select/deselect."
)

PREMIUM_ALREADY_ACTIVE_TEXT: Final[str] = (
    "✅ Premium is already active. You don't need to purchase again."
)

PREMIUM_ALREADY_HAVE_TEXT: Final[str] = (
    "You already have Premium."
)

PREMIUM_UNKNOWN_PRODUCT_TEXT: Final[str] = (
    "Unknown product"
)

PREMIUM_ACTIVATED_TEXT: Final[str] = (
    "✅ Premium activated. You can now use multiple sources."
)

PREMIUM_ALREADY_ACTIVATED_TEXT: Final[str] = (
    "✅ Premium is already activated."
)

