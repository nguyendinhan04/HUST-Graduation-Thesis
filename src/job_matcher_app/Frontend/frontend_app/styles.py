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
            padding-top: 1.25rem;
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

        .skill-row {
            padding: 13px 0;
            border-bottom: 1px solid #e8e4de;
            font-weight: 600;
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

        dialog[open] .discard-confirm {
            position: fixed !important;
            top: 96px !important;
            left: 50% !important;
            transform: translateX(-50%) !important;
            width: min(400px, calc(100vw - 48px)) !important;
            z-index: 1000002 !important;
            box-sizing: border-box !important;
            padding: 24px 28px 18px !important;
            background: #ffffff !important;
            border: 1px solid #d7d3cc !important;
            border-bottom: 0 !important;
            border-radius: 8px 8px 0 0 !important;
            box-shadow: 0 18px 56px rgba(0, 0, 0, 0.28) !important;
        }

        dialog[open] .discard-title {
            color: #191919;
            font-size: 22px;
            font-weight: 650;
            line-height: 1.25;
            margin-bottom: 18px;
        }

        dialog[open] .discard-message {
            color: #191919;
            font-size: 16px;
            line-height: 1.45;
            max-width: 460px;
        }

        dialog[open] .discard-confirm + div[data-testid="stHorizontalBlock"] {
            position: fixed !important;
            top: 231px !important;
            left: 50% !important;
            transform: translateX(-50%) !important;
            width: min(400px, calc(100vw - 48px)) !important;
            z-index: 1000003 !important;
            box-sizing: border-box !important;
            margin: 0 !important;
            padding: 14px 28px 16px !important;
            background: #ffffff !important;
            border: 1px solid #d7d3cc !important;
            border-top: 1px solid #e8e4de !important;
            border-radius: 0 0 8px 8px !important;
            box-shadow: none !important;
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

