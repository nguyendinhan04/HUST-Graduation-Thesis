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

        .stApp:has([data-testid="stDialog"])::before,
        .stApp:has(dialog[open])::before,
        .stApp:has([role="dialog"])::before {
            content: "";
            position: fixed;
            inset: 0;
            background: rgba(0, 0, 0, 0.58);
            backdrop-filter: blur(1px);
            z-index: 999998;
            pointer-events: none;
        }

        [data-testid="stDialog"],
        dialog[open],
        [role="dialog"] {
            position: fixed !important;
            top: 52% !important;
            left: 50% !important;
            transform: translate(-50%, -50%) !important;
            width: min(640px, calc(100vw - 56px)) !important;
            max-width: min(640px, calc(100vw - 56px)) !important;
            max-height: min(78vh, 760px) !important;
            margin: 0 !important;
            padding: 0 !important;
            background: #ffffff !important;
            border: 1px solid #c8c2b8 !important;
            border-radius: 16px !important;
            box-shadow: 0 24px 80px rgba(0, 0, 0, 0.42) !important;
            outline: none !important;
            overflow: hidden !important;
            z-index: 999999 !important;
        }

        [data-testid="stDialog"] > div,
        dialog[open] > div,
        [role="dialog"] > div {
            background: #ffffff !important;
            border-radius: 16px !important;
            max-height: min(78vh, 760px) !important;
            overflow-y: auto !important;
            padding: 18px 24px 22px !important;
        }

        [data-testid="stDialog"] div[data-testid="stVerticalBlock"],
        dialog[open] div[data-testid="stVerticalBlock"],
        [role="dialog"] div[data-testid="stVerticalBlock"] {
            gap: 0.75rem;
        }

        [data-testid="stDialog"] div[data-testid="column"]:last-child button,
        dialog[open] div[data-testid="column"]:last-child button,
        [role="dialog"] div[data-testid="column"]:last-child button {
            min-height: 34px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

