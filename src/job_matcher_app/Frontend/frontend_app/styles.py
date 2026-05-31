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

        .dialog-backdrop {
            position: fixed;
            inset: 0;
            background: rgba(0, 0, 0, 0.58);
            backdrop-filter: blur(1px);
            z-index: 999990;
            pointer-events: auto;
        }

        dialog[open]::backdrop {
            background: rgba(0, 0, 0, 0.58) !important;
            backdrop-filter: blur(1px);
        }

        [data-testid="stDialog"],
        dialog[open],
        [role="dialog"] {
            position: fixed !important;
            top: 50% !important;
            left: 50% !important;
            transform: translate(-50%, -50%) !important;
            width: min(760px, calc(100vw - 32px)) !important;
            max-width: min(760px, calc(100vw - 32px)) !important;
            height: min(760px, calc(100dvh - 32px)) !important;
            max-height: min(760px, calc(100dvh - 32px)) !important;
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

        [data-testid="stDialog"] > div,
        dialog[open] > div,
        [role="dialog"] > div {
            background: #ffffff !important;
            border-radius: 10px !important;
            height: 100% !important;
            max-height: 100% !important;
            box-sizing: border-box !important;
            overflow-y: auto !important;
            padding: 0 28px 92px !important;
            overscroll-behavior: contain;
        }

        [data-testid="stDialog"] > div > div,
        dialog[open] > div > div,
        [role="dialog"] > div > div {
            min-height: 100% !important;
            display: flex !important;
            flex-direction: column !important;
            justify-content: flex-start !important;
            align-items: stretch !important;
        }

        [data-testid="stDialog"] div[data-testid="stVerticalBlock"],
        dialog[open] div[data-testid="stVerticalBlock"],
        [role="dialog"] div[data-testid="stVerticalBlock"] {
            justify-content: flex-start !important;
            align-items: stretch !important;
            gap: 0.75rem;
        }

        [data-testid="stDialog"] form,
        dialog[open] form,
        [role="dialog"] form {
            width: min(100%, 680px) !important;
            margin: 0 auto !important;
            padding-bottom: 0 !important;
        }

        [data-testid="stDialog"] form label,
        dialog[open] form label,
        [role="dialog"] form label {
            font-size: 15px !important;
            color: #191919 !important;
            font-weight: 400 !important;
        }

        [data-testid="stDialog"] form input,
        [data-testid="stDialog"] form textarea,
        [data-testid="stDialog"] form [data-baseweb="select"] > div,
        dialog[open] form input,
        dialog[open] form textarea,
        dialog[open] form [data-baseweb="select"] > div,
        [role="dialog"] form input,
        [role="dialog"] form textarea,
        [role="dialog"] form [data-baseweb="select"] > div {
            background: #ffffff !important;
            border-color: #666666 !important;
            color: #191919 !important;
            border-radius: 4px !important;
            min-height: 40px !important;
        }

        [data-testid="stDialog"] form input:focus,
        [data-testid="stDialog"] form textarea:focus,
        dialog[open] form input:focus,
        dialog[open] form textarea:focus,
        [role="dialog"] form input:focus,
        [role="dialog"] form textarea:focus {
            border-color: #0a66c2 !important;
            box-shadow: 0 0 0 1px #0a66c2 inset !important;
        }

        [data-testid="stDialog"] form div[data-testid="stHorizontalBlock"]:has(div[data-testid="stFormSubmitButton"]),
        dialog[open] form div[data-testid="stHorizontalBlock"]:has(div[data-testid="stFormSubmitButton"]),
        [role="dialog"] form div[data-testid="stHorizontalBlock"]:has(div[data-testid="stFormSubmitButton"]) {
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

        [data-testid="stDialog"] div[data-testid="column"]:last-child button,
        dialog[open] div[data-testid="column"]:last-child button,
        [role="dialog"] div[data-testid="column"]:last-child button {
            min-height: 36px;
            border-radius: 999px !important;
        }

        @media (max-width: 640px) {
            [data-testid="stDialog"],
            dialog[open],
            [role="dialog"] {
                width: calc(100vw - 16px) !important;
                max-width: calc(100vw - 16px) !important;
                height: calc(100dvh - 16px) !important;
                max-height: calc(100dvh - 16px) !important;
                border-radius: 10px !important;
            }

            [data-testid="stDialog"] > div,
            dialog[open] > div,
            [role="dialog"] > div {
                height: 100% !important;
                max-height: 100% !important;
                padding: 0 16px 88px !important;
            }

            [data-testid="stDialog"] form div[data-testid="stHorizontalBlock"]:has(div[data-testid="stFormSubmitButton"]),
            dialog[open] form div[data-testid="stHorizontalBlock"]:has(div[data-testid="stFormSubmitButton"]),
            [role="dialog"] form div[data-testid="stHorizontalBlock"]:has(div[data-testid="stFormSubmitButton"]) {
                bottom: 8px !important;
                width: calc(100vw - 18px) !important;
                padding: 12px 14px 14px !important;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

