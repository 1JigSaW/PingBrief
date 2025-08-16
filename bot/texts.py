"""Centralized user-facing texts for the Telegram bot.

All texts are English-only to keep the product consistent and easy to
internationalize in the future.
"""

from typing import Final


WELCOME_NEW_USER_TEXT: Final[str] = (
    "🚀 <b>Welcome to PingBrief!</b>\n\n"
    "📰 <b>Your personal news aggregator</b>\n\n"
    "Choose the news sources that interest you:\n"
    "• Click on sources to select/deselect\n"
    "• Select at least one source to continue\n"
    "• We'll send you fresh articles daily"
)


WELCOME_EXISTING_USER_TEXT: Final[str] = (
    "🎉 <b>Welcome back!</b>\n\n"
    "You have <b>{count} active subscription(s)</b>:\n\n"
    "{sources}\n\n"
    "📬 We'll send you fresh news from these source(s)!"
)


HELP_TEXT: Final[str] = (
    "🤖 <b>PingBrief Bot Help</b>\n\n"
    "📰 <b>What is PingBrief?</b>\n"
    "Your personal news aggregator that sends you fresh articles from your favorite sources.\n\n"
    "📋 <b>Available Commands:</b>\n"
    "• <code>/start</code> - Start the bot or create new subscriptions\n"
    "• <code>/settings</code> - Manage your existing subscriptions\n"
    "• <code>/help</code> - Show this help message\n\n"
    "🎯 <b>How it works:</b>\n"
    "1. Choose news sources you're interested in\n"
    "2. Select your preferred language\n"
    "3. Get daily news digests in your Telegram\n\n"
    "⚙️ <b>Features:</b>\n"
    "• Multiple news sources\n"
    "• 15+ supported languages\n"
    "• Daily news summaries\n"
    "• Easy subscription management\n\n"
    "💡 <b>Tip:</b> Use <code>/settings</code> to add more sources or change languages!"
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
    "⚙️ <b>Subscription Settings</b>\n\n"
    "You have <b>{count} active subscription(s)</b>:\n\n"
    "{sources}\n\n"
    "Choose an action:"
)


ADD_SUBSCRIPTION_HEADER_TEXT: Final[str] = (
    "📰 <b>Add New Subscription</b>\n\n"
    "Choose news sources for your new subscription:\n"
    "• Click on sources to select/deselect\n"
    "• Select at least one source to continue"
)


SELECTED_SOURCES_TEXT: Final[str] = (
    "📰 <b>Selected Sources</b>\n\n"
    "You've selected <b>{count} source(s)</b>:\n\n"
    "{sources}\n\n"
    "🌍 Now choose the language for your subscription:"
)


SUBSCRIPTION_CREATED_TEXT: Final[str] = (
    "🎉 <b>Subscription Created Successfully!</b>\n\n"
    "📰 <b>Source(s):</b>\n{sources}\n\n"
    "🌍 <b>Language:</b> {flag} {language}\n\n"
    "📬 <b>What's next?</b>\n"
    "We'll send you fresh articles from these source(s) daily!\n\n"
    "⚙️ Click the button below to manage your subscription"
)


REMOVED_SUBSCRIPTION_TEXT: Final[str] = (
    "🗑️ <b>Subscription removed</b>\n\n"
    "✅ Your subscription has been deactivated.\n\n"
    "Click the button below to create a new subscription!"
)


SUBSCRIPTION_UPDATED_TEXT: Final[str] = (
    "✅ <b>Subscription Updated</b>\n\n"
    "📰 <b>Source(s):</b>\n{sources}\n\n"
    "🌍 <b>Language:</b> {flag} {language}\n\n"
    "⚙️ You can manage your subscription below."
)


START_FLOW_HEADER_TEXT: Final[str] = WELCOME_NEW_USER_TEXT

