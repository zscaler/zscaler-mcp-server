import React from "react";
import clsx from "clsx";
import { translate } from "@docusaurus/Translate";
import type { Props } from "@theme/ColorModeToggle";

import styles from "./styles.module.css";

/**
 * Slide-style color-mode toggle — replaces Docusaurus's stock single-icon
 * click-toggle. Renders a horizontal pill with a sun icon on the left
 * track, a moon icon on the right, and a sliding circular knob that
 * indicates the active mode. Clicking anywhere on the track flips the
 * mode.
 *
 * Props mirror @theme/ColorModeToggle so this swizzle stays drop-in
 * compatible across Docusaurus minor versions:
 *   - value:           current mode ("light" | "dark")
 *   - onChange:        called with the next mode
 *   - className:       optional outer wrapper class
 *   - buttonClassName: forwarded to the actual <button> for navbar polish
 */
export default function ColorModeToggle({
  className,
  buttonClassName,
  value,
  onChange,
}: Props): React.JSX.Element {
  const isDark = value === "dark";
  const nextMode = isDark ? "light" : "dark";

  const ariaLabel = translate(
    {
      message: "Switch between dark and light mode (currently {mode} mode)",
      id: "theme.colorToggle.ariaLabel",
      description: "The ARIA label for the navbar color mode toggle",
    },
    {
      mode: isDark
        ? translate({
            message: "dark",
            id: "theme.colorToggle.ariaLabel.mode.dark",
            description: "The name for the dark color mode",
          })
        : translate({
            message: "light",
            id: "theme.colorToggle.ariaLabel.mode.light",
            description: "The name for the light color mode",
          }),
    },
  );

  return (
    <div className={clsx(styles.toggle, className)}>
      <button
        type="button"
        className={clsx(
          "clean-btn",
          styles.toggleButton,
          isDark && styles.toggleButtonDark,
          buttonClassName,
        )}
        title={ariaLabel}
        aria-label={ariaLabel}
        aria-live="polite"
        aria-pressed={isDark}
        onClick={() => onChange(nextMode)}
      >
        <SunIcon
          className={clsx(styles.toggleIcon, styles.toggleSun, !isDark && styles.toggleIconActive)}
        />
        <MoonIcon
          className={clsx(styles.toggleIcon, styles.toggleMoon, isDark && styles.toggleIconActive)}
        />
        <span className={styles.toggleKnob} aria-hidden="true" />
      </button>
    </div>
  );
}

function SunIcon({ className }: { className?: string }): React.JSX.Element {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      width="14"
      height="14"
      fill="currentColor"
      aria-hidden="true"
    >
      <path d="M12 7a5 5 0 1 0 0 10 5 5 0 0 0 0-10zm0-5a1 1 0 0 1 1 1v2a1 1 0 1 1-2 0V3a1 1 0 0 1 1-1zm0 17a1 1 0 0 1 1 1v2a1 1 0 1 1-2 0v-2a1 1 0 0 1 1-1zM4.22 4.22a1 1 0 0 1 1.42 0l1.41 1.41a1 1 0 1 1-1.41 1.42L4.22 5.64a1 1 0 0 1 0-1.42zm12.73 12.73a1 1 0 0 1 1.42 0l1.41 1.41a1 1 0 0 1-1.41 1.42l-1.42-1.42a1 1 0 0 1 0-1.41zM2 12a1 1 0 0 1 1-1h2a1 1 0 1 1 0 2H3a1 1 0 0 1-1-1zm17 0a1 1 0 0 1 1-1h2a1 1 0 1 1 0 2h-2a1 1 0 0 1-1-1zM4.22 19.78a1 1 0 0 1 0-1.42l1.41-1.41a1 1 0 1 1 1.42 1.41l-1.42 1.42a1 1 0 0 1-1.41 0zm12.73-12.73a1 1 0 0 1 0-1.42l1.41-1.41a1 1 0 1 1 1.42 1.42l-1.42 1.41a1 1 0 0 1-1.41 0z" />
    </svg>
  );
}

function MoonIcon({ className }: { className?: string }): React.JSX.Element {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      width="14"
      height="14"
      fill="currentColor"
      aria-hidden="true"
    >
      <path d="M21 12.79A9 9 0 1 1 11.21 3a7 7 0 0 0 9.79 9.79z" />
    </svg>
  );
}
