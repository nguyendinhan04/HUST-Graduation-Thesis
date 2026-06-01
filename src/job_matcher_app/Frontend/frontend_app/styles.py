from __future__ import annotations

import streamlit as st


def inject_linkedin_styles() -> None:
    st.markdown(
        """
        <style>
        .stApp {
            background: #f3f2ef;
            color: #191919;
        }

        .block-container {
            max-width: 980px;
            padding-top: 3.25rem;
            padding-bottom: 3rem;
        }

        div[data-testid="stSidebar"] {
            background: #ffffff;
            border-right: 1px solid #d7d3cc;
        }

        .linkedin-card {
            background: #ffffff;
            border: 1px solid #d7d3cc;
            border-radius: 8px;
            margin: 0 0 8px 0;
            overflow: hidden;
        }

        div[data-testid="stVerticalBlockBorderWrapper"] {
            background: #ffffff !important;
            border-color: #d7d3cc !important;
            border-radius: 8px !important;
        }

        div[data-testid="stVerticalBlockBorderWrapper"] > div {
            background: #ffffff !important;
            border-radius: 8px !important;
        }

        .st-key-profile-experiences-card,
        .st-key-profile-educations-card,
        .st-key-profile-skills-card,
        .st-key-management-experience-header-card,
        .st-key-management-education-header-card,
        .st-key-management-skills-header-card,
        .st-key-management-experiences-empty-card,
        .st-key-management-experiences-list-card,
        .st-key-management-educations-empty-card,
        .st-key-management-educations-list-card,
        .st-key-management-skills-empty-card,
        .st-key-management-skills-list-card {
            background: #ffffff !important;
            background-color: #ffffff !important;
            border-color: #d7d3cc !important;
            border-radius: 8px !important;
        }

        .st-key-profile-experiences-card > div,
        .st-key-profile-educations-card > div,
        .st-key-profile-skills-card > div,
        .st-key-management-experience-header-card > div,
        .st-key-management-education-header-card > div,
        .st-key-management-skills-header-card > div,
        .st-key-management-experiences-empty-card > div,
        .st-key-management-experiences-list-card > div,
        .st-key-management-educations-empty-card > div,
        .st-key-management-educations-list-card > div,
        .st-key-management-skills-empty-card > div,
        .st-key-management-skills-list-card > div {
            background: #ffffff !important;
            background-color: #ffffff !important;
            border-radius: 8px !important;
        }

        .st-key-profile-experiences-card div[data-testid="stVerticalBlock"],
        .st-key-profile-experiences-card div[data-testid="stHorizontalBlock"],
        .st-key-profile-experiences-card div[data-testid="column"],
        .st-key-profile-experiences-card div[data-testid="stElementContainer"],
        .st-key-profile-experiences-card div[data-testid="stMarkdownContainer"],
        .st-key-profile-educations-card div[data-testid="stVerticalBlock"],
        .st-key-profile-educations-card div[data-testid="stHorizontalBlock"],
        .st-key-profile-educations-card div[data-testid="column"],
        .st-key-profile-educations-card div[data-testid="stElementContainer"],
        .st-key-profile-educations-card div[data-testid="stMarkdownContainer"],
        .st-key-profile-skills-card div[data-testid="stVerticalBlock"],
        .st-key-profile-skills-card div[data-testid="stHorizontalBlock"],
        .st-key-profile-skills-card div[data-testid="column"],
        .st-key-profile-skills-card div[data-testid="stElementContainer"],
        .st-key-profile-skills-card div[data-testid="stMarkdownContainer"],
        .st-key-management-experience-header-card div[data-testid="stVerticalBlock"],
        .st-key-management-experience-header-card div[data-testid="stHorizontalBlock"],
        .st-key-management-experience-header-card div[data-testid="column"],
        .st-key-management-experience-header-card div[data-testid="stElementContainer"],
        .st-key-management-experience-header-card div[data-testid="stMarkdownContainer"],
        .st-key-management-education-header-card div[data-testid="stVerticalBlock"],
        .st-key-management-education-header-card div[data-testid="stHorizontalBlock"],
        .st-key-management-education-header-card div[data-testid="column"],
        .st-key-management-education-header-card div[data-testid="stElementContainer"],
        .st-key-management-education-header-card div[data-testid="stMarkdownContainer"],
        .st-key-management-skills-header-card div[data-testid="stVerticalBlock"],
        .st-key-management-skills-header-card div[data-testid="stHorizontalBlock"],
        .st-key-management-skills-header-card div[data-testid="column"],
        .st-key-management-skills-header-card div[data-testid="stElementContainer"],
        .st-key-management-skills-header-card div[data-testid="stMarkdownContainer"],
        .st-key-management-experiences-empty-card div[data-testid="stVerticalBlock"],
        .st-key-management-experiences-empty-card div[data-testid="stHorizontalBlock"],
        .st-key-management-experiences-empty-card div[data-testid="column"],
        .st-key-management-experiences-empty-card div[data-testid="stElementContainer"],
        .st-key-management-experiences-empty-card div[data-testid="stMarkdownContainer"],
        .st-key-management-experiences-list-card div[data-testid="stVerticalBlock"],
        .st-key-management-experiences-list-card div[data-testid="stHorizontalBlock"],
        .st-key-management-experiences-list-card div[data-testid="column"],
        .st-key-management-experiences-list-card div[data-testid="stElementContainer"],
        .st-key-management-experiences-list-card div[data-testid="stMarkdownContainer"],
        .st-key-management-educations-empty-card div[data-testid="stVerticalBlock"],
        .st-key-management-educations-empty-card div[data-testid="stHorizontalBlock"],
        .st-key-management-educations-empty-card div[data-testid="column"],
        .st-key-management-educations-empty-card div[data-testid="stElementContainer"],
        .st-key-management-educations-empty-card div[data-testid="stMarkdownContainer"],
        .st-key-management-educations-list-card div[data-testid="stVerticalBlock"],
        .st-key-management-educations-list-card div[data-testid="stHorizontalBlock"],
        .st-key-management-educations-list-card div[data-testid="column"],
        .st-key-management-educations-list-card div[data-testid="stElementContainer"],
        .st-key-management-educations-list-card div[data-testid="stMarkdownContainer"],
        .st-key-management-skills-empty-card div[data-testid="stVerticalBlock"],
        .st-key-management-skills-empty-card div[data-testid="stHorizontalBlock"],
        .st-key-management-skills-empty-card div[data-testid="column"],
        .st-key-management-skills-empty-card div[data-testid="stElementContainer"],
        .st-key-management-skills-empty-card div[data-testid="stMarkdownContainer"],
        .st-key-management-skills-list-card div[data-testid="stVerticalBlock"],
        .st-key-management-skills-list-card div[data-testid="stHorizontalBlock"],
        .st-key-management-skills-list-card div[data-testid="column"],
        .st-key-management-skills-list-card div[data-testid="stElementContainer"],
        .st-key-management-skills-list-card div[data-testid="stMarkdownContainer"] {
            background: transparent !important;
            background-color: transparent !important;
        }

        .st-key-management-experiences-list-card div[data-testid="stDivider"],
        .st-key-management-educations-list-card div[data-testid="stDivider"],
        .st-key-management-skills-list-card div[data-testid="stDivider"] {
            margin: 0 !important;
        }

        .st-key-management-experiences-list-card > div > div[data-testid="stVerticalBlock"],
        .st-key-management-educations-list-card > div > div[data-testid="stVerticalBlock"],
        .st-key-management-skills-list-card > div > div[data-testid="stVerticalBlock"] {
            gap: 0.35rem !important;
        }

        .st-key-management-experiences-list-card div[data-testid="stDivider"] > div,
        .st-key-management-educations-list-card div[data-testid="stDivider"] > div,
        .st-key-management-skills-list-card div[data-testid="stDivider"] > div {
            margin: 0 !important;
        }

        .st-key-management-experiences-list-card div[data-testid="stDivider"] hr,
        .st-key-management-educations-list-card div[data-testid="stDivider"] hr,
        .st-key-management-skills-list-card div[data-testid="stDivider"] hr {
            margin: 0 !important;
            border-color: #d7d3cc !important;
        }

        .profile-cover {
            height: 96px;
            background: linear-gradient(135deg, #0a66c2 0%, #378fe9 56%, #dce6f1 100%);
        }

        .profile-body {
            padding: 0 24px 22px;
        }

        .profile-avatar {
            width: 128px;
            height: 128px;
            border-radius: 50%;
            border: 4px solid #ffffff;
            margin-top: -64px;
            background: #eef3f8;
            object-fit: cover;
            display: block;
        }

        .profile-avatar-placeholder {
            width: 128px;
            height: 128px;
            border-radius: 50%;
            border: 4px solid #ffffff;
            margin-top: -64px;
            background: #eef3f8;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #56687a;
            font-size: 42px;
            font-weight: 700;
        }

        .profile-name {
            margin: 12px 0 0;
            font-size: 26px;
            font-weight: 650;
            line-height: 1.2;
        }

        .profile-headline {
            margin-top: 4px;
            font-size: 16px;
            color: #191919;
        }

        .muted {
            color: #666666;
            font-size: 14px;
        }

        .section-title {
            font-size: 20px;
            font-weight: 650;
            margin: 2px 0 12px;
        }

        .entity-row {
            display: grid;
            grid-template-columns: 48px minmax(0, 1fr);
            gap: 12px;
            padding: 12px 0 14px;
            border-bottom: 1px solid #e8e4de;
        }

        .management-entity-row {
            border-bottom: 0;
            padding: 12px 0;
        }

        .entity-logo {
            width: 48px;
            height: 48px;
            border-radius: 4px;
            background: #eef3f8;
            color: #56687a;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 700;
            font-size: 13px;
            text-align: center;
        }

        .entity-title {
            font-weight: 650;
            line-height: 1.25;
            margin-bottom: 2px;
        }

        .entity-subtitle {
            color: #191919;
            line-height: 1.35;
            font-size: 14px;
        }

        .entity-meta {
            color: #666666;
            font-size: 13px;
            line-height: 1.35;
        }

        .entity-desc {
            margin-top: 8px;
            color: #191919;
            font-size: 14px;
            line-height: 1.45;
            white-space: pre-wrap;
        }

        .skill-line {
            margin-top: 8px;
            font-size: 13px;
            font-weight: 600;
        }

        .skill-line-spacer {
            height: 12px;
        }

        .skill-row {
            padding: 13px 0;
            border-bottom: 1px solid #e8e4de;
            font-weight: 600;
        }

        .skills-filter-row {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            align-items: center;
            margin: 2px 0 16px;
        }

        .skill-filter-pill {
            display: inline-flex;
            align-items: center;
            min-height: 34px;
            padding: 0 14px;
            border: 1px solid #a8a8a8;
            border-radius: 999px;
            color: #404040;
            background: #ffffff;
            font-size: 15px;
            font-weight: 600;
            line-height: 1;
            white-space: nowrap;
        }

        .skill-filter-pill.active {
            color: #ffffff;
            background: #23583d;
            border-color: #23583d;
        }

        .linkedin-skill-row {
            padding: 18px 0 16px;
            border-bottom: 1px solid #e8e4de;
        }

        .linkedin-skill-name {
            color: #191919;
            font-size: 18px;
            font-weight: 650;
            line-height: 1.3;
        }

        .linkedin-skill-source {
            display: flex;
            align-items: center;
            gap: 12px;
            margin-top: 14px;
            color: #404040;
            font-size: 15px;
            line-height: 1.35;
        }

        .skill-source-logo {
            width: 28px;
            min-width: 28px;
            height: 28px;
            border-radius: 4px;
            background: #eef3f8;
            color: #56687a;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 10px;
            font-weight: 700;
            text-align: center;
        }

        .skill-source-text {
            min-width: 0;
            overflow-wrap: anywhere;
        }

        .add-skill-context,
        dialog[open] .add-skill-context {
            margin: 18px 0 16px;
        }

        .add-skill-context-title,
        dialog[open] .add-skill-context-title {
            color: #191919;
            font-size: 20px;
            font-weight: 650;
            line-height: 1.3;
            margin-bottom: 2px;
        }

        .add-skill-context-copy,
        dialog[open] .add-skill-context-copy {
            color: #404040;
            font-size: 14px;
            line-height: 1.4;
        }

        .add-skill-group-label,
        dialog[open] .add-skill-group-label {
            color: #666666;
            font-size: 14px;
            font-weight: 500;
            margin: 16px 0 6px;
        }

        .empty-state {
            color: #666666;
            padding: 4px 0 18px;
        }

        div.stButton > button {
            border-radius: 999px;
            border: 0;
            background: transparent;
            color: #191919;
            min-height: 36px;
            font-weight: 600;
            width: 100%;
        }

        div.stButton > button:hover {
            background: #ebebeb;
            color: #191919;
            border: 0;
        }

        button[kind="primary"],
        div[data-testid="stFormSubmitButton"] button[kind="primary"] {
            background: #0a66c2 !important;
            border: 1px solid #0a66c2 !important;
            color: #ffffff !important;
            box-shadow: none !important;
        }

        button[kind="primary"]:hover,
        div[data-testid="stFormSubmitButton"] button[kind="primary"]:hover {
            background: #004182 !important;
            border: 1px solid #004182 !important;
            color: #ffffff !important;
        }

        .form-loading,
        dialog[open] .form-loading {
            display: flex;
            align-items: center;
            gap: 10px;
            width: min(100%, 680px);
            box-sizing: border-box;
            margin: 8px auto 10px;
            padding: 11px 14px;
            color: #191919;
            background: #eef3f8;
            border: 1px solid #c7d7e8;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 600;
        }

        .form-loading-spinner,
        dialog[open] .form-loading-spinner {
            width: 18px;
            height: 18px;
            min-width: 18px;
            border: 3px solid #b7c9db;
            border-top-color: #0a66c2;
            border-radius: 50%;
            animation: form-loading-spin 0.8s linear infinite;
        }

        @keyframes form-loading-spin {
            to {
                transform: rotate(360deg);
            }
        }

        div[data-testid="stExpander"] {
            background: #ffffff;
            border: 1px solid #d7d3cc;
            border-radius: 8px;
            margin-bottom: 10px;
        }

        .stTabs [data-baseweb="tab-list"] {
            gap: 4px;
        }

        dialog[open]::backdrop {
            background: rgba(0, 0, 0, 0.58) !important;
            backdrop-filter: blur(1px);
        }

        dialog[open] {
            position: fixed !important;
            top: 16px !important;
            left: 50% !important;
            transform: translateX(-50%) !important;
            width: min(760px, calc(100vw - 32px)) !important;
            max-width: min(760px, calc(100vw - 32px)) !important;
            height: auto !important;
            max-height: calc(100dvh - 32px) !important;
            margin: 0 !important;
            padding: 0 !important;
            background: #ffffff !important;
            border: 1px solid #c8c2b8 !important;
            border-radius: 10px !important;
            box-sizing: border-box !important;
            box-shadow: 0 24px 80px rgba(0, 0, 0, 0.42) !important;
            outline: none !important;
            overflow: hidden !important;
            z-index: 999999 !important;
        }

        dialog[open] [data-testid="stDialog"],
        dialog[open] [role="dialog"] {
            position: static !important;
            width: auto !important;
            max-width: none !important;
            height: auto !important;
            max-height: none !important;
            margin: 0 !important;
            padding: 0 !important;
            background: transparent !important;
            border: 0 !important;
            border-radius: 0 !important;
            box-shadow: none !important;
            outline: none !important;
            overflow: visible !important;
        }

        dialog[open] > div {
            background: #ffffff !important;
            border-radius: 10px !important;
            height: auto !important;
            max-height: calc(100dvh - 34px) !important;
            box-sizing: border-box !important;
            overflow-y: auto !important;
            padding: 0 28px 84px !important;
            overscroll-behavior: contain;
        }

        dialog[open] > button,
        dialog[open] button[aria-label="Close"],
        dialog[open] button[aria-label="Close dialog"],
        dialog[open] button[title="Close"],
        dialog[open] header button,
        dialog[open] [data-testid="stDialogCloseButton"] {
            display: none !important;
        }

        dialog[open] header,
        dialog[open] [data-testid="stDialogHeader"],
        dialog[open] [data-testid="stDialogTitle"] {
            display: none !important;
        }

        div[style*="padding: 1.5rem 1.5rem 0.75rem"][style*="max-height: 80vh"][style*="flex-direction: row"]:has(.custom-dialog-title),
        dialog[open] div[style*="padding: 1.5rem"][style*="max-height: 80vh"][style*="flex-direction: row"]:has(.custom-dialog-title) {
            margin: 0 !important;
            padding: 0.25rem 1.5rem 0.5rem !important;
            max-height: none !important;
        }

        dialog[open] div[style*="padding: 1.5rem"][style*="font-size: 1.5rem"]:not(:has(.custom-dialog-title)),
        dialog[open] div[style*="font-size: 1.5rem"][style*="font-weight: 600"]:not(:has(.custom-dialog-title)),
        dialog[open] div[style*="font-weight: 600"][style*="flex-direction: row"]:not(:has(.custom-dialog-title)),
        dialog[open] div[style*="max-height: 80vh"][style*="flex-direction: row"]:not(:has(.custom-dialog-title)) {
            display: none !important;
            height: 0 !important;
            min-height: 0 !important;
            max-height: 0 !important;
            margin: 0 !important;
            padding: 0 !important;
            overflow: hidden !important;
        }

        dialog[open] [data-testid="stDialog"] > div:first-child:not(:has(.custom-dialog-title)),
        dialog[open] [role="dialog"] > div:first-child:not(:has(.custom-dialog-title)),
        dialog[open] div:has(> h1):not(:has(.custom-dialog-title)),
        dialog[open] div:has(> h2):not(:has(.custom-dialog-title)),
        dialog[open] div:has(> h3):not(:has(.custom-dialog-title)),
        dialog[open] div[data-testid="stVerticalBlock"] > div:has(h1):not(:has(.custom-dialog-title)),
        dialog[open] div[data-testid="stVerticalBlock"] > div:has(h2):not(:has(.custom-dialog-title)),
        dialog[open] div[data-testid="stVerticalBlock"] > div:has(h3):not(:has(.custom-dialog-title)) {
            display: none !important;
            height: 0 !important;
            min-height: 0 !important;
            margin: 0 !important;
            padding: 0 !important;
            overflow: hidden !important;
        }

        dialog[open] div[data-testid="stVerticalBlock"]:has(.custom-dialog-title) {
            gap: 0.35rem !important;
            padding-top: 0 !important;
        }

        div[data-testid="stHorizontalBlock"]:has(.custom-dialog-title),
        dialog[open] div[data-testid="stHorizontalBlock"]:has(.custom-dialog-title) {
            position: sticky !important;
            top: 0 !important;
            z-index: 6 !important;
            align-items: center !important;
            width: 100% !important;
            box-sizing: border-box !important;
            margin: 0 0 10px !important;
            padding: 6px 0 8px !important;
            background: #ffffff !important;
            border-bottom: 1px solid #e8e4de !important;
        }

        .custom-dialog-title,
        dialog[open] .custom-dialog-title {
            color: #191919;
            font-size: 34px !important;
            font-weight: 800 !important;
            line-height: 1.1 !important;
            margin: 0 !important;
            padding: 0 !important;
        }

        div[data-testid="stHorizontalBlock"]:has(.custom-dialog-title) button,
        dialog[open] div[data-testid="stHorizontalBlock"]:has(.custom-dialog-title) button {
            width: 42px !important;
            min-width: 42px !important;
            max-width: 42px !important;
            height: 42px !important;
            min-height: 42px !important;
            max-height: 42px !important;
            padding: 0 !important;
            border-radius: 8px !important;
            color: #333333 !important;
            font-size: 32px !important;
            font-weight: 500 !important;
            line-height: 1 !important;
            aspect-ratio: 1 / 1 !important;
        }

        dialog[open]:has(.discard-confirm-backdrop)::after {
            content: "" !important;
            position: fixed !important;
            inset: 0 !important;
            z-index: 1000010 !important;
            background: rgba(0, 0, 0, 0.46) !important;
            backdrop-filter: blur(1px);
            pointer-events: auto;
        }

        .discard-confirm-backdrop,
        dialog[open] .discard-confirm-backdrop {
            position: fixed !important;
            inset: 0 !important;
            z-index: 1000011 !important;
            background: rgba(0, 0, 0, 0.46) !important;
            backdrop-filter: blur(1px);
            pointer-events: auto;
        }

        .discard-confirm,
        dialog[open] .discard-confirm {
            position: fixed !important;
            top: calc(33vh - 82px) !important;
            left: 50% !important;
            transform: translateX(-50%) !important;
            width: min(400px, calc(100vw - 48px)) !important;
            min-height: 164px !important;
            z-index: 1000020 !important;
            box-sizing: border-box !important;
            padding: 24px 28px 16px !important;
            background: #ffffff !important;
            border: 1px solid #d7d3cc !important;
            border-bottom: 0 !important;
            border-radius: 8px 8px 0 0 !important;
            box-shadow: 0 18px 56px rgba(0, 0, 0, 0.28) !important;
        }

        .discard-title,
        dialog[open] .discard-title {
            color: #191919;
            font-size: 22px;
            font-weight: 650;
            line-height: 1.25;
            margin-bottom: 18px;
        }

        .discard-message,
        dialog[open] .discard-message {
            color: #191919;
            font-size: 16px;
            line-height: 1.45;
            max-width: 460px;
        }

        .discard-confirm-actions-marker,
        div[data-testid="stElementContainer"]:has(.discard-confirm-actions-marker),
        div[data-testid="stMarkdownContainer"]:has(.discard-confirm-actions-marker),
        dialog[open] div[data-testid="stElementContainer"]:has(.discard-confirm-actions-marker),
        dialog[open] div[data-testid="stMarkdownContainer"]:has(.discard-confirm-actions-marker) {
            width: 0 !important;
            height: 0 !important;
            margin: 0 !important;
            padding: 0 !important;
            overflow: hidden !important;
        }

        div[data-testid="stHorizontalBlock"]:has(.discard-confirm-actions-marker),
        dialog[open] div[data-testid="stHorizontalBlock"]:has(.discard-confirm-actions-marker) {
            position: fixed !important;
            top: calc(33vh + 82px) !important;
            left: 50% !important;
            transform: translateX(-50%) !important;
            width: min(400px, calc(100vw - 48px)) !important;
            z-index: 1000030 !important;
            box-sizing: border-box !important;
            margin: 0 !important;
            padding: 12px 28px 18px !important;
            background: #ffffff !important;
            border: 1px solid #d7d3cc !important;
            border-top: 1px solid #e8e4de !important;
            border-radius: 0 0 8px 8px !important;
            box-shadow: none !important;
        }

        div[data-testid="stHorizontalBlock"]:has(.discard-confirm-actions-marker) div[data-testid="column"] {
            min-width: 92px !important;
        }

        div[data-testid="stHorizontalBlock"]:has(.discard-confirm-actions-marker) button {
            min-width: 92px !important;
            white-space: nowrap !important;
            padding: 0 18px !important;
        }

        dialog[open] > div > div {
            min-height: 0 !important;
            display: flex !important;
            flex-direction: column !important;
            justify-content: flex-start !important;
            align-items: stretch !important;
        }

        dialog[open] div[data-testid="stVerticalBlock"] {
            justify-content: flex-start !important;
            align-items: stretch !important;
            gap: 0.45rem !important;
        }

        dialog[open] div[data-testid="stVerticalBlockBorderWrapper"] {
            margin-top: 0 !important;
        }

        dialog[open] form {
            width: min(100%, 680px) !important;
            margin: 8px auto 8px !important;
            padding-bottom: 0 !important;
        }

        dialog[open] form > div {
            gap: 0.55rem !important;
        }

        dialog[open] form label,
        dialog[open] label {
            font-size: 15px !important;
            color: #191919 !important;
            font-weight: 400 !important;
        }

        dialog[open] form input,
        dialog[open] form textarea,
        dialog[open] form [data-baseweb="select"] > div,
        dialog[open] input,
        dialog[open] textarea,
        dialog[open] [data-baseweb="select"] > div {
            background: #ffffff !important;
            border-color: #666666 !important;
            color: #191919 !important;
            border-radius: 4px !important;
            min-height: 40px !important;
        }

        dialog[open] form input:focus,
        dialog[open] form textarea:focus,
        dialog[open] input:focus,
        dialog[open] textarea:focus {
            border-color: #0a66c2 !important;
            box-shadow: 0 0 0 1px #0a66c2 inset !important;
        }

        dialog[open] form div[data-testid="stHorizontalBlock"]:has(div[data-testid="stFormSubmitButton"]),
        dialog[open] div[data-testid="stHorizontalBlock"]:has(button[kind="primary"]) {
            position: fixed !important;
            bottom: 16px !important;
            left: 50% !important;
            transform: translateX(-50%) !important;
            width: min(758px, calc(100vw - 34px)) !important;
            z-index: 1000000;
            align-items: center;
            margin: 0 !important;
            padding: 14px 20px 16px !important;
            background: #ffffff;
            border-top: 1px solid #e8e4de;
            border-radius: 0 0 10px 10px;
            box-shadow: 0 -2px 10px rgba(0, 0, 0, 0.04);
        }

        dialog[open] div[data-testid="column"]:last-child button {
            min-height: 36px;
            border-radius: 999px !important;
        }

        </style>
        """,
        unsafe_allow_html=True,
    )

