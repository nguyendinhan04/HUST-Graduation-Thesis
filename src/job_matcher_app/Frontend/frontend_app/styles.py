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

        div[data-testid="stSidebar"] [data-testid="stSidebarContent"] {
            padding: 28px 16px 22px;
            position: relative;
            min-height: 100dvh;
            padding-bottom: 168px;
        }

        .sidebar-brand {
            display: grid;
            grid-template-columns: 42px minmax(0, 1fr);
            gap: 10px;
            align-items: center;
            margin: 2px 0 26px;
        }

        .sidebar-brand-mark {
            width: 42px;
            height: 42px;
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #ffffff;
            background: #0ea5e9;
            font-size: 14px;
            font-weight: 800;
            letter-spacing: 0;
        }

        .sidebar-brand-title {
            color: #111827;
            font-size: 18px;
            font-weight: 760;
            line-height: 1.2;
        }

        .sidebar-brand-subtitle {
            color: #6b7280;
            font-size: 12px;
            line-height: 1.35;
            margin-top: 2px;
        }

        .sidebar-section-label {
            color: #4b5563;
            font-size: 15px;
            font-weight: 800;
            line-height: 1;
            margin: 0 0 4px;
            text-transform: none;
            letter-spacing: 0;
        }

        .st-key-sidebar-navigator {
            margin-top: 14px;
        }

        .st-key-sidebar-navigator div[data-testid="stVerticalBlock"] {
            gap: 0 !important;
        }

        .st-key-sidebar-navigator div[data-testid="stLayoutWrapper"] {
            margin: 0 !important;
            padding: 0 !important;
        }

        .st-key-sidebar-navigator div[data-testid="stElementContainer"]:has(.st-key-sidebar-nav-profile),
        .st-key-sidebar-navigator div[data-testid="stElementContainer"]:has(.st-key-sidebar-nav-explore),
        .st-key-sidebar-navigator div[data-testid="stElementContainer"]:has(.st-key-sidebar-nav-recommendations),
        .st-key-sidebar-navigator div[data-testid="stElementContainer"]:has(.st-key-sidebar-nav-dashboard) {
            margin: 0 !important;
            padding: 0 !important;
        }

        .st-key-sidebar-navigator .st-key-sidebar-nav-profile button,
        .st-key-sidebar-navigator .st-key-sidebar-nav-explore button,
        .st-key-sidebar-navigator .st-key-sidebar-nav-recommendations button,
        .st-key-sidebar-navigator .st-key-sidebar-nav-dashboard button,
        .st-key-sidebar-nav-profile button,
        .st-key-sidebar-nav-explore button,
        .st-key-sidebar-nav-recommendations button,
        .st-key-sidebar-nav-dashboard button {
            width: 100% !important;
            min-height: 46px !important;
            display: flex !important;
            align-items: center !important;
            justify-content: flex-start !important;
            padding: 0 14px !important;
            color: #4b5563 !important;
            background: transparent !important;
            border: 1px solid transparent !important;
            border-radius: 8px !important;
            font-size: 18px !important;
            font-weight: 500 !important;
            text-align: left !important;
        }

        .st-key-sidebar-navigator .st-key-sidebar-nav-profile button > div,
        .st-key-sidebar-navigator .st-key-sidebar-nav-explore button > div,
        .st-key-sidebar-navigator .st-key-sidebar-nav-recommendations button > div,
        .st-key-sidebar-navigator .st-key-sidebar-nav-dashboard button > div,
        .st-key-sidebar-navigator .st-key-sidebar-nav-profile button span,
        .st-key-sidebar-navigator .st-key-sidebar-nav-explore button span,
        .st-key-sidebar-navigator .st-key-sidebar-nav-recommendations button span,
        .st-key-sidebar-navigator .st-key-sidebar-nav-dashboard button span,
        .st-key-sidebar-navigator .st-key-sidebar-nav-profile button p,
        .st-key-sidebar-navigator .st-key-sidebar-nav-explore button p,
        .st-key-sidebar-navigator .st-key-sidebar-nav-recommendations button p,
        .st-key-sidebar-navigator .st-key-sidebar-nav-dashboard button p,
        .st-key-sidebar-nav-profile button > div,
        .st-key-sidebar-nav-explore button > div,
        .st-key-sidebar-nav-recommendations button > div,
        .st-key-sidebar-nav-dashboard button > div,
        .st-key-sidebar-nav-profile button span,
        .st-key-sidebar-nav-explore button span,
        .st-key-sidebar-nav-recommendations button span,
        .st-key-sidebar-nav-dashboard button span,
        .st-key-sidebar-nav-profile button p,
        .st-key-sidebar-nav-explore button p,
        .st-key-sidebar-nav-recommendations button p,
        .st-key-sidebar-nav-dashboard button p {
            width: 100% !important;
            margin: 0 !important;
            text-align: left !important;
            justify-content: flex-start !important;
        }

        .st-key-sidebar-navigator .st-key-sidebar-nav-profile button:hover,
        .st-key-sidebar-navigator .st-key-sidebar-nav-explore button:hover,
        .st-key-sidebar-navigator .st-key-sidebar-nav-recommendations button:hover,
        .st-key-sidebar-navigator .st-key-sidebar-nav-dashboard button:hover,
        .st-key-sidebar-nav-profile button:hover,
        .st-key-sidebar-nav-explore button:hover,
        .st-key-sidebar-nav-recommendations button:hover,
        .st-key-sidebar-nav-dashboard button:hover {
            color: #111827 !important;
            background: #eef0f5 !important;
            border-color: #eef0f5 !important;
        }

        .sidebar-user {
            display: grid;
            grid-template-columns: 40px minmax(0, 1fr);
            gap: 10px;
            align-items: center;
            margin: 0 0 14px;
        }

        .sidebar-footer-marker {
            width: 0;
            height: 0;
            margin: 0;
            padding: 0;
            overflow: hidden;
        }

        .sidebar-footer {
            position: fixed;
            left: 16px;
            bottom: 78px;
            width: calc(100% - 32px);
            max-width: 240px;
            box-sizing: border-box;
            z-index: 10;
        }

        .st-key-sidebar-signout {
            position: fixed;
            left: 16px;
            bottom: 24px;
            width: calc(100% - 32px);
            max-width: 240px;
            z-index: 10;
        }

        .st-key-sidebar-signout button {
            min-height: 40px !important;
            border-radius: 8px !important;
            color: #111827 !important;
            background: transparent !important;
        }

        .st-key-sidebar-signout button:hover {
            color: #075985 !important;
            background: #f0f9ff !important;
        }

        .sidebar-user-avatar {
            width: 40px;
            height: 40px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #075985;
            background: #e0f2fe;
            border: 1px solid #bae6fd;
            font-size: 13px;
            font-weight: 800;
        }

        .sidebar-user-label {
            color: #6b7280;
            font-size: 11px;
            font-weight: 720;
            line-height: 1.25;
            text-transform: uppercase;
        }

        .sidebar-user-email {
            color: #111827;
            font-size: 13px;
            font-weight: 620;
            line-height: 1.35;
            overflow-wrap: anywhere;
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
            gap: 0 !important;
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

        .management-divider {
            height: 1px;
            width: 100%;
            margin: 0;
            padding: 0;
            background: #e8e4de;
        }

        .st-key-management-experiences-list-card div[data-testid="stElementContainer"]:has(.management-divider),
        .st-key-management-educations-list-card div[data-testid="stElementContainer"]:has(.management-divider),
        .st-key-management-experiences-list-card div[data-testid="stMarkdownContainer"]:has(.management-divider),
        .st-key-management-educations-list-card div[data-testid="stMarkdownContainer"]:has(.management-divider),
        .st-key-management-experiences-list-card div[data-testid="stMarkdown"]:has(.management-divider),
        .st-key-management-educations-list-card div[data-testid="stMarkdown"]:has(.management-divider) {
            margin: 0 !important;
            padding: 0 !important;
            min-height: 0 !important;
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
            padding: 12px 0 14px;
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
            background: #0369a1;
            border-color: #0369a1;
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

        .recommendation-title {
            color: #191919;
            font-size: 26px;
            font-weight: 750;
            line-height: 1.2;
            margin: 0 0 4px;
        }

        .recommendation-subtitle {
            color: #666666;
            font-size: 14px;
            line-height: 1.4;
            margin: 0 0 14px;
        }

        .explore-result-count {
            color: #4b5563;
            font-size: 14px;
            font-weight: 700;
            line-height: 1.35;
            margin: 2px 0 10px;
        }

        .explore-pagination-meta {
            color: #4b5563;
            font-size: 14px;
            font-weight: 700;
            line-height: 38px;
            text-align: center;
        }

        div[class*="st-key-job-card-wrap-"] {
            position: relative;
            min-height: 194px;
            margin: 0 0 12px;
            padding: 7px;
            overflow: hidden;
        }

        .job-card {
            display: grid;
            grid-template-columns: 150px minmax(0, 1fr);
            gap: 14px;
            height: 180px;
            box-sizing: border-box;
            padding: 16px;
            margin: 0;
            background: #f0f9ff;
            border: 1px solid #38bdf8;
            border-radius: 18px;
            cursor: pointer;
            transition: border-color 0.16s ease, box-shadow 0.16s ease, outline-color 0.16s ease;
            outline: 1px solid transparent;
            outline-offset: 2px;
        }

        div[class*="st-key-job-card-wrap-"]:hover .job-card {
            border-color: #0ea5e9;
            box-shadow: 0 8px 24px rgba(14, 165, 233, 0.16);
            outline-color: rgba(14, 165, 233, 0.35);
        }

        div[class*="st-key-job-card-wrap-"] div[data-testid="stButton"],
        div[class*="st-key-job-card-click-"] {
            position: absolute !important;
            inset: 0 !important;
            z-index: 20 !important;
            margin: 0 !important;
            padding: 0 !important;
            width: 100% !important;
            height: 180px !important;
            min-height: 180px !important;
            max-height: 180px !important;
            top: 7px !important;
            left: 7px !important;
            right: 7px !important;
            bottom: auto !important;
            width: calc(100% - 14px) !important;
        }

        div[class*="st-key-job-card-wrap-"] div[data-testid="stButton"] > button,
        div[class*="st-key-job-card-click-"] > div,
        div[class*="st-key-job-card-click-"] button {
            width: 100% !important;
            height: 180px !important;
            min-height: 180px !important;
            max-height: 180px !important;
            margin: 0 !important;
            padding: 0 !important;
            opacity: 0 !important;
            cursor: pointer !important;
            border: 0 !important;
            border-radius: 18px !important;
            background: transparent !important;
        }

        .job-card-media {
            display: flex;
            align-items: stretch;
            min-height: 0;
        }

        .job-card-logo,
        .job-card-logo-placeholder {
            width: 100%;
            height: 148px;
            min-height: 0;
            border: 1px solid #d7d3cc;
            border-radius: 12px;
            background: #ffffff;
            object-fit: contain;
            box-sizing: border-box;
        }

        .job-card-logo-placeholder {
            display: flex;
            align-items: center;
            justify-content: center;
            color: #56687a;
            font-size: 28px;
            font-weight: 800;
        }

        .job-card-body {
            min-width: 0;
            min-height: 0;
            height: 148px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            gap: 10px;
        }

        .job-card-main {
            display: grid;
            grid-template-columns: minmax(0, 1fr) max-content;
            gap: 16px;
            align-items: start;
            min-height: 0;
        }

        .job-card-main > div {
            min-width: 0;
        }

        .job-card-title {
            color: #24324a;
            font-size: 20px;
            font-weight: 750;
            line-height: 1.25;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }

        .job-card-company {
            color: #767f8d;
            font-size: 15px;
            font-weight: 600;
            line-height: 1.35;
            margin-top: 10px;
            text-transform: uppercase;
            overflow-wrap: anywhere;
        }

        .job-tag-row {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-top: 10px;
        }

        .job-tag {
            display: inline-flex;
            align-items: center;
            min-height: 30px;
            padding: 0 12px;
            border-radius: 999px;
            color: #191919;
            background: #f0f1f3;
            font-size: 14px;
            font-weight: 600;
        }

        .job-card-salary {
            color: #0284c7;
            font-size: 17px;
            font-weight: 750;
            line-height: 1.3;
            white-space: nowrap;
            text-align: right;
        }

        .job-card-footer {
            display: grid;
            grid-template-columns: minmax(0, 1fr) max-content;
            gap: 12px;
            align-items: center;
            min-height: 46px;
            padding-top: 10px;
            border-top: 1px solid #edf2ef;
        }

        .job-card-meta,
        .job-card-posted {
            color: #767f8d;
            font-size: 15px;
            font-weight: 600;
            line-height: 1.35;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }

        .job-card-posted {
            text-align: right;
        }

        .job-detail-hero {
            background: #ffffff;
            border: 1px solid #d7d3cc;
            border-radius: 8px;
            box-sizing: border-box;
            margin: 8px 0 12px;
            padding: 18px 22px;
        }

        .job-detail-title-row {
            margin-bottom: 18px;
        }

        .job-detail-title {
            color: #191919;
            font-size: 23px;
            font-weight: 750;
            line-height: 1.3;
            overflow-wrap: anywhere;
        }

        .job-detail-company {
            color: #404040;
            font-size: 14px;
            font-weight: 600;
            line-height: 1.35;
            margin-top: 4px;
            overflow-wrap: anywhere;
        }

        .job-detail-stat-grid {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 18px;
            margin: 4px 0 16px;
        }

        .job-detail-stat {
            display: grid;
            grid-template-columns: 42px minmax(0, 1fr);
            gap: 10px;
            align-items: center;
            min-width: 0;
        }

        .job-detail-icon {
            width: 38px;
            height: 38px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #ffffff;
            background: #0ea5e9;
            font-size: 18px;
            font-weight: 750;
            line-height: 1;
        }

        .job-detail-stat-label {
            color: #404040;
            font-size: 13px;
            font-weight: 650;
            line-height: 1.25;
        }

        .job-detail-stat-value {
            color: #191919;
            font-size: 14px;
            font-weight: 650;
            line-height: 1.35;
            overflow-wrap: anywhere;
        }

        .job-detail-deadline {
            color: #404040;
            font-size: 14px;
            line-height: 1.35;
            padding-top: 2px;
        }

        .job-detail-section {
            background: #ffffff;
            border: 1px solid #d7d3cc;
            border-radius: 8px;
            box-sizing: border-box;
            margin: 10px 0;
            padding: 18px 22px;
        }

        .job-detail-section-title {
            color: #191919;
            font-size: 18px;
            font-weight: 750;
            line-height: 1.3;
            margin-bottom: 10px;
        }

        .job-detail-section-body {
            color: #191919;
            font-size: 14px;
            line-height: 1.55;
        }

        .job-detail-section-body ul {
            margin: 0;
            padding-left: 20px;
        }

        .job-detail-section-body li {
            margin: 0 0 6px;
        }

        .job-detail-paragraph {
            white-space: pre-wrap;
        }

        .job-detail-empty {
            color: #666666;
        }

        .job-detail-skills {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-top: 12px;
        }

        .job-detail-skill {
            display: inline-flex;
            align-items: center;
            min-height: 30px;
            padding: 0 12px;
            border-radius: 999px;
            color: #0369a1;
            background: #e0f2fe;
            border: 1px solid #7dd3fc;
            font-size: 13px;
            font-weight: 650;
        }

        .skill-gap-summary {
            display: grid;
            grid-template-columns: minmax(0, 0.8fr) minmax(0, 1.2fr);
            gap: 18px;
            align-items: center;
            margin-bottom: 12px;
        }

        .skill-gap-label {
            color: #666666;
            font-size: 13px;
            font-weight: 650;
            line-height: 1.3;
        }

        .skill-gap-score {
            color: #075985;
            font-size: 30px;
            font-weight: 800;
            line-height: 1.1;
            margin-top: 4px;
        }

        .skill-gap-count-grid {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 8px;
        }

        .skill-gap-count {
            min-height: 54px;
            box-sizing: border-box;
            padding: 9px 10px;
            border: 1px solid #d7d3cc;
            border-radius: 8px;
            color: #666666;
            background: #f8fafc;
            font-size: 12px;
            font-weight: 650;
            line-height: 1.25;
        }

        .skill-gap-count span {
            display: block;
            color: #191919;
            font-size: 18px;
            font-weight: 800;
            line-height: 1.1;
            margin-bottom: 3px;
        }

        .skill-gap-progress {
            width: 100%;
            height: 10px;
            overflow: hidden;
            border-radius: 999px;
            background: #e5e7eb;
            margin: 8px 0 16px;
        }

        .skill-gap-progress-fill {
            height: 100%;
            border-radius: 999px;
            background: #0ea5e9;
        }

        .skill-gap-missing-title {
            color: #404040;
            font-size: 14px;
            font-weight: 750;
            line-height: 1.35;
            margin: 0 0 8px;
        }

        .skill-gap-chip-row {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
        }

        .skill-gap-missing-chip {
            display: inline-flex;
            align-items: center;
            min-height: 30px;
            padding: 0 12px;
            border-radius: 999px;
            color: #92400e;
            background: #fff7ed;
            border: 1px solid #fed7aa;
            font-size: 13px;
            font-weight: 650;
        }

        .skill-gap-complete {
            color: #166534;
            background: #f0fdf4;
            border: 1px solid #bbf7d0;
            border-radius: 8px;
            box-sizing: border-box;
            padding: 10px 12px;
            font-size: 14px;
            font-weight: 650;
        }

        .skill-gap-info {
            color: #666666;
            background: #f8fafc;
            border: 1px solid #d7d3cc;
            border-radius: 8px;
            box-sizing: border-box;
            padding: 10px 12px;
            font-size: 14px;
            font-weight: 650;
        }

        .st-key-job_detail_back button {
            border: 1px solid #a8a8a8 !important;
            background: #ffffff !important;
            color: #404040 !important;
        }

        .st-key-job_detail_back button:hover {
            background: #f3f2ef !important;
            border-color: #666666 !important;
        }

        div[class*="st-key-job_apply_"] button[kind="primary"] {
            background: #0ea5e9 !important;
            border: 1px solid #0ea5e9 !important;
            color: #ffffff !important;
        }

        div[class*="st-key-job_apply_"] button[kind="primary"]:hover {
            background: #0284c7 !important;
            border-color: #0284c7 !important;
            color: #ffffff !important;
        }

        div[class*="st-key-job_apply_"] button:disabled,
        div[class*="st-key-job_apply_"] button[kind="primary"]:disabled {
            background: #d8dee4 !important;
            border-color: #c6cdd4 !important;
            color: #7a8590 !important;
            cursor: not-allowed !important;
            opacity: 0.72 !important;
        }

        .job-apply-error-dialog,
        dialog[open] .job-apply-error-dialog {
            margin: 20px 0 18px;
        }

        .job-apply-error-title,
        dialog[open] .job-apply-error-title {
            color: #191919;
            font-size: 24px;
            font-weight: 750;
            line-height: 1.25;
            margin-bottom: 10px;
        }

        .job-apply-error-message,
        dialog[open] .job-apply-error-message {
            color: #5f1b1b;
            background: #fff1f2;
            border: 1px solid #fecdd3;
            border-radius: 8px;
            box-sizing: border-box;
            padding: 12px 14px;
            font-size: 15px;
            font-weight: 650;
            line-height: 1.45;
        }

        @media (max-width: 720px) {
            .job-card {
                grid-template-columns: 88px minmax(0, 1fr);
                gap: 12px;
                padding: 12px;
                height: auto;
                min-height: 180px;
            }

            .job-card-logo,
            .job-card-logo-placeholder {
                height: 88px;
            }

            .job-card-body {
                height: auto;
                min-height: 156px;
            }

            .job-card-main,
            .job-card-footer {
                grid-template-columns: 1fr;
            }

            .job-card-salary,
            .job-card-posted {
                text-align: left;
                white-space: normal;
            }

            .job-detail-hero,
            .job-detail-section {
                padding: 16px;
            }

            .job-detail-stat-grid {
                grid-template-columns: 1fr;
                gap: 14px;
            }

            .skill-gap-summary,
            .skill-gap-count-grid {
                grid-template-columns: 1fr;
            }

            div[class*="st-key-job-card-wrap-"] {
                min-height: 194px;
            }

            div[class*="st-key-job-card-wrap-"] div[data-testid="stButton"],
            div[class*="st-key-job-card-click-"],
            div[class*="st-key-job-card-wrap-"] div[data-testid="stButton"] > button,
            div[class*="st-key-job-card-click-"] > div,
            div[class*="st-key-job-card-click-"] button {
                height: 100% !important;
                min-height: 180px !important;
                max-height: none !important;
            }
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

        .skills-editor-header,
        dialog[open] .skills-editor-header {
            margin: 18px 0 12px;
        }

        .skills-editor-title,
        dialog[open] .skills-editor-title {
            color: #191919;
            font-size: 20px;
            font-weight: 650;
            line-height: 1.3;
            margin-bottom: 4px;
        }

        .skills-editor-copy,
        dialog[open] .skills-editor-copy {
            color: #404040;
            font-size: 13px;
            line-height: 1.35;
        }

        .skills-editor-item-name,
        dialog[open] .skills-editor-item-name {
            min-height: 42px;
            display: flex;
            align-items: center;
            color: #191919;
            font-size: 15px;
            font-weight: 650;
            line-height: 1.3;
            padding: 4px 0;
        }

        .auth-form-section-title {
            color: #111827;
            font-size: 15px;
            font-weight: 800;
            line-height: 1.25;
            margin: 12px 0 8px;
        }

        .employer-summary {
            background: #ffffff;
            border: 1px solid #d7d3cc;
            border-radius: 8px;
            margin: 14px 0 14px;
            padding: 18px;
        }

        .employer-summary-header {
            display: grid;
            grid-template-columns: 72px minmax(0, 1fr);
            gap: 14px;
            align-items: center;
        }

        .employer-company-logo,
        .employer-company-logo-placeholder {
            width: 72px;
            height: 72px;
            border-radius: 8px;
            border: 1px solid #d7d3cc;
            background: #f8fafc;
        }

        .employer-company-logo {
            object-fit: cover;
            display: block;
        }

        .employer-company-logo-placeholder {
            display: flex;
            align-items: center;
            justify-content: center;
            color: #075985;
            background: #e0f2fe;
            font-size: 18px;
            font-weight: 800;
        }

        .employer-title-row {
            display: flex;
            gap: 10px;
            align-items: center;
            justify-content: space-between;
            min-width: 0;
        }

        .employer-company-name {
            min-width: 0;
            color: #111827;
            font-size: 24px;
            font-weight: 800;
            line-height: 1.2;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }

        .employer-company-link {
            flex: 0 0 auto;
            color: #0a66c2 !important;
            font-size: 13px;
            font-weight: 800;
            text-decoration: none !important;
        }

        .employer-profile-line {
            color: #4b5563;
            font-size: 14px;
            line-height: 1.35;
            margin-top: 4px;
        }

        .employer-fact-row {
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
            margin-top: 10px;
        }

        .employer-fact {
            color: #374151;
            background: #f3f4f6;
            border: 1px solid #e5e7eb;
            border-radius: 999px;
            font-size: 12px;
            font-weight: 700;
            line-height: 1;
            padding: 7px 10px;
        }

        .employer-description {
            color: #374151;
            font-size: 14px;
            line-height: 1.55;
            margin-top: 16px;
        }

        .employer-description-muted,
        .employer-missing-note {
            color: #6b7280;
            font-size: 13px;
            font-weight: 600;
        }

        .employer-missing-note {
            margin-top: 10px;
        }

        .employer-section-title {
            color: #111827;
            font-size: 22px;
            font-weight: 800;
            line-height: 1.25;
            margin: 8px 0 10px;
        }

        .employer-section-title span {
            color: #6b7280;
            font-size: 15px;
            font-weight: 700;
        }

        .employer-job-list {
            display: grid;
            gap: 8px;
        }

        .employer-job-row {
            display: grid;
            grid-template-columns: minmax(0, 1fr) 210px;
            gap: 18px;
            align-items: start;
            background: #ffffff;
            border: 1px solid #d7d3cc;
            border-radius: 8px;
            margin-bottom: 8px;
            padding: 15px 16px;
        }

        .employer-job-main {
            min-width: 0;
        }

        .employer-job-title {
            color: #111827;
            font-size: 17px;
            font-weight: 800;
            line-height: 1.35;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }

        .employer-job-meta {
            color: #6b7280;
            font-size: 13px;
            line-height: 1.4;
            margin-top: 7px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }

        .employer-job-side {
            display: grid;
            justify-items: end;
            gap: 5px;
            text-align: right;
        }

        .employer-job-status {
            border-radius: 999px;
            color: #374151;
            background: #f3f4f6;
            border: 1px solid #e5e7eb;
            font-size: 12px;
            font-weight: 800;
            line-height: 1;
            padding: 6px 9px;
        }

        .employer-job-status-open {
            color: #065f46;
            background: #ecfdf5;
            border-color: #a7f3d0;
        }

        .employer-job-status-draft {
            color: #92400e;
            background: #fffbeb;
            border-color: #fde68a;
        }

        .employer-job-status-closed {
            color: #991b1b;
            background: #fef2f2;
            border-color: #fecaca;
        }

        .employer-job-salary {
            color: #0f172a;
            font-size: 14px;
            font-weight: 800;
            line-height: 1.3;
        }

        .employer-job-date {
            color: #6b7280;
            font-size: 12px;
            line-height: 1.3;
        }

        @media (max-width: 720px) {
            .employer-summary-header,
            .employer-job-row {
                grid-template-columns: 1fr;
            }

            .employer-title-row {
                align-items: flex-start;
                flex-direction: column;
            }

            .employer-company-name,
            .employer-job-title,
            .employer-job-meta {
                white-space: normal;
            }

            .employer-job-side {
                justify-items: start;
                text-align: left;
            }
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

