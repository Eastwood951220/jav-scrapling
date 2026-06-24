import type { ThemeConfig } from "antd";

/**
 * Ant Design 5 theme configuration.
 *
 * Design tokens follow the Data-Dense Dashboard style:
 * - Primary: #1E40AF (deep blue for trust/precision)
 * - Secondary: #3B82F6 (medium blue for interactive elements)
 * - CTA/Warning: #F59E0B (amber for highlights)
 * - Background: #F8FAFC (light slate for readability)
 * - Text: #1E3A8A (dark navy for contrast)
 */
const sharedTokens: ThemeConfig["token"] = {
  colorPrimary: "#1E40AF",
  colorLink: "#3B82F6",
  colorWarning: "#F59E0B",
  fontFamily:
    '"Fira Sans", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
  borderRadius: 6,
  colorBgContainer: "#FFFFFF",
  colorBgLayout: "#F8FAFC",
  colorText: "#1E3A8A",
  colorTextSecondary: "#475569",
};

export const lightTheme: ThemeConfig = {
  token: sharedTokens,
  components: {
    Layout: {
      siderBg: "#0F172A",
      headerBg: "#FFFFFF",
      bodyBg: "#F8FAFC",
      headerHeight: 56,
    },
    Menu: {
      darkItemBg: "#0F172A",
      darkItemSelectedBg: "#1E40AF",
    },
    Table: {
      headerBg: "#F1F5F9",
      rowHoverBg: "#EEF2FF",
    },
  },
};

/** Stub dark theme for future use. Swap `algorithm` with `theme.darkAlgorithm` when ready. */
export const darkTheme: ThemeConfig = {
  token: {
    ...sharedTokens,
    colorBgContainer: "#1E293B",
    colorBgLayout: "#0F172A",
    colorText: "#E2E8F0",
    colorTextSecondary: "#94A3B8",
  },
  components: {
    ...lightTheme.components,
    Layout: {
      siderBg: "#020617",
      headerBg: "#1E293B",
      bodyBg: "#0F172A",
      headerHeight: 56,
    },
    Table: {
      headerBg: "#1E293B",
      rowHoverBg: "#1E3A5F",
    },
  },
};
