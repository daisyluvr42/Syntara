/**
 * Text input with search history autocomplete.
 * Shows suggestions as user types; Tab accepts the top suggestion.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { getSearchHistory } from "../../services/api";
import styles from "./AutocompleteInput.module.css";

interface AutocompleteInputProps {
  value: string;
  onChange: (v: string) => void;
  onKeyDown?: (e: React.KeyboardEvent<HTMLInputElement>) => void;
  placeholder?: string;
  lang: string;
  className?: string;
}

export default function AutocompleteInput({
  value,
  onChange,
  onKeyDown,
  placeholder,
  lang,
  className,
}: AutocompleteInputProps) {
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [showDropdown, setShowDropdown] = useState(false);
  const [selectedIdx, setSelectedIdx] = useState(-1);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const wrapperRef = useRef<HTMLDivElement>(null);

  // Fetch suggestions with debounce
  const fetchSuggestions = useCallback(
    (prefix: string) => {
      if (timerRef.current) clearTimeout(timerRef.current);
      if (!prefix.trim()) {
        // Show recent history when input is focused but empty
        timerRef.current = setTimeout(async () => {
          try {
            const resp = await getSearchHistory(lang, "", 8);
            setSuggestions(resp.suggestions);
            setShowDropdown(resp.suggestions.length > 0);
            setSelectedIdx(-1);
          } catch {
            setSuggestions([]);
          }
        }, 100);
        return;
      }
      timerRef.current = setTimeout(async () => {
        try {
          const resp = await getSearchHistory(lang, prefix, 8);
          // Filter out exact match
          const filtered = resp.suggestions.filter(
            (s) => s.toLowerCase() !== prefix.toLowerCase()
          );
          setSuggestions(filtered);
          setShowDropdown(filtered.length > 0);
          setSelectedIdx(-1);
        } catch {
          setSuggestions([]);
        }
      }, 150);
    },
    [lang]
  );

  useEffect(() => {
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, []);

  // Close dropdown on outside click
  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target as Node)) {
        setShowDropdown(false);
      }
    };
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const v = e.target.value;
    onChange(v);
    fetchSuggestions(v);
  };

  const handleFocus = () => {
    fetchSuggestions(value);
  };

  const acceptSuggestion = (suggestion: string) => {
    onChange(suggestion);
    setShowDropdown(false);
    setSuggestions([]);
  };

  const handleKeyDownInner = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (showDropdown && suggestions.length > 0) {
      if (e.key === "Tab") {
        e.preventDefault();
        const target = selectedIdx >= 0 ? suggestions[selectedIdx] : suggestions[0];
        if (target) acceptSuggestion(target);
        return;
      }
      if (e.key === "ArrowDown") {
        e.preventDefault();
        setSelectedIdx((prev) => Math.min(prev + 1, suggestions.length - 1));
        return;
      }
      if (e.key === "ArrowUp") {
        e.preventDefault();
        setSelectedIdx((prev) => Math.max(prev - 1, -1));
        return;
      }
      if (e.key === "Escape") {
        setShowDropdown(false);
        return;
      }
    }
    onKeyDown?.(e);
  };

  // Inline ghost text (top suggestion after current input)
  const ghostText =
    suggestions.length > 0 && value.trim() && suggestions[0].toLowerCase().startsWith(value.toLowerCase())
      ? suggestions[0]
      : "";

  return (
    <div className={styles.wrapper} ref={wrapperRef}>
      <div className={styles.inputContainer}>
        {ghostText && (
          <div className={`${styles.ghost} ${className || ""}`}>
            <span className={styles.ghostHidden}>{value}</span>
            <span className={styles.ghostSuffix}>{ghostText.slice(value.length)}</span>
          </div>
        )}
        <input
          type="text"
          value={value}
          onChange={handleChange}
          onKeyDown={handleKeyDownInner}
          onFocus={handleFocus}
          placeholder={placeholder}
          className={className}
          autoComplete="off"
        />
      </div>
      {showDropdown && suggestions.length > 0 && (
        <div className={styles.dropdown}>
          {suggestions.map((s, i) => (
            <button
              key={s}
              type="button"
              className={`${styles.suggestion} ${i === selectedIdx ? styles.suggestionActive : ""}`}
              onMouseDown={() => acceptSuggestion(s)}
              onMouseEnter={() => setSelectedIdx(i)}
            >
              {s}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
