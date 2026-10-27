"""Explicit screen renderer registry and persistent device footer."""

from app.ui.components import footer
from app.ui.router import UIScreen
from app.ui.screens import (
    about,
    account,
    assessment_menu,
    chapters,
    confidence,
    content_updates,
    detail,
    device_info,
    diagnostics,
    home,
    leave_confirm,
    navigator,
    packs,
    pairing,
    profile,
    progress,
    question,
    result,
    review,
    settings,
    software_update,
    subjects,
    submit_confirm,
    sync,
    test_setup,
    text_entry,
    wifi,
)

RENDERERS = {
    UIScreen.PROFILE: profile.render,
    UIScreen.WELCOME: profile.render,
    UIScreen.HOME: home.render,
    UIScreen.SUBJECTS: subjects.render,
    UIScreen.CHAPTERS: chapters.render,
    UIScreen.PACKS: packs.render,
    UIScreen.TEST_SETUP: test_setup.render,
    UIScreen.QUESTION: question.render,
    UIScreen.CONFIDENCE: confidence.render,
    UIScreen.QUESTION_NAV: navigator.render,
    UIScreen.ASSESSMENT_MENU: assessment_menu.render,
    UIScreen.LEAVE_CONFIRM: leave_confirm.render,
    UIScreen.SUBMIT_CONFIRM: submit_confirm.render,
    UIScreen.RESULT: result.render,
    UIScreen.REVIEW: review.render,
    UIScreen.QUESTION_DETAIL: detail.render,
    UIScreen.PROGRESS: progress.render,
    UIScreen.SETTINGS: settings.render,
    UIScreen.PIN: text_entry.render,
    UIScreen.ADD_PROFILE: text_entry.render,
    UIScreen.PAIRING: pairing.render,
    UIScreen.WIFI: wifi.render,
    UIScreen.SYNC: sync.render,
    UIScreen.ACCOUNT: account.render,
    UIScreen.CONTENT_UPDATES: content_updates.render,
    UIScreen.SOFTWARE_UPDATE: software_update.render,
    UIScreen.DEVICE_INFO: device_info.render,
    UIScreen.STATUS: device_info.render,
    UIScreen.DIAGNOSTICS: diagnostics.render,
    UIScreen.ABOUT: about.render,
}


def render(surface, controller, fonts):
    controls = RENDERERS[controller.screen](surface, controller, fonts)
    footer(surface, controller, fonts)
    return controls
