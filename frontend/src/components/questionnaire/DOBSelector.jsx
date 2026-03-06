import React, { useEffect, useMemo, useState } from 'react';
import adultFemaleImage from '../../assets/questionnaire/3/adult-female.png';
import adultMaleImage from '../../assets/questionnaire/3/adult-male.png';
import teenFemaleImage from '../../assets/questionnaire/3/teen-female.png';
import legendFemaleImage from '../../assets/questionnaire/3/legend-female.png';
import legendMaleImage from '../../assets/questionnaire/3/legend-male.png';
import teenMaleImage from '../../assets/questionnaire/3/teen-male.png';
import './DOBSelector.css';

const MONTHS = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
];
const MIN_AGE_YEARS = 15;

export function isLeapYear(year) {
  if (!Number.isInteger(year)) return false;
  if (year % 400 === 0) return true;
  if (year % 100 === 0) return false;
  return year % 4 === 0;
}

export function getDaysInMonth(year, month) {
  if (!Number.isInteger(year) || !Number.isInteger(month) || month < 1 || month > 12) return 31;
  if (month === 2) return isLeapYear(year) ? 29 : 28;
  if ([4, 6, 9, 11].includes(month)) return 30;
  return 31;
}

export function calculateAgeFromDOB(year, month, day) {
  if (!year || !month || !day) return null;
  const today = new Date();
  const birth = new Date(year, month - 1, day);
  if (Number.isNaN(birth.getTime()) || birth > today) return null;
  let age = today.getFullYear() - year;
  const hasHadBirthday =
    today.getMonth() > month - 1
    || (today.getMonth() === month - 1 && today.getDate() >= day);
  if (!hasHadBirthday) age -= 1;
  return age >= 0 ? age : null;
}

function calculatePreviewAge(year, month, day) {
  if (!year) return null;
  const now = new Date();
  const resolvedMonth = month || (now.getMonth() + 1);
  const resolvedDay = day || now.getDate();
  let age = now.getFullYear() - year;
  const hasHadBirthday =
    now.getMonth() > resolvedMonth - 1
    || (now.getMonth() === resolvedMonth - 1 && now.getDate() >= resolvedDay);
  if (!hasHadBirthday) age -= 1;
  return age >= 0 ? age : null;
}

export function getAgeStage(age) {
  if (!Number.isFinite(age)) return null;
  if (age < 20) return { key: 'teen', label: 'Teen', emoji: '🎮' };
  if (age < 50) return { key: 'adult', label: 'Adult', emoji: '🧠' };
  return { key: 'legend', label: 'Legend', emoji: '👑' };
}

function getStageImage(stageKey, gender) {
  const normalizedGender = gender === 'female' ? 'female' : 'male';
  if (stageKey === 'teen') return normalizedGender === 'female' ? teenFemaleImage : teenMaleImage;
  if (stageKey === 'legend') return normalizedGender === 'female' ? legendFemaleImage : legendMaleImage;
  return normalizedGender === 'female' ? adultFemaleImage : adultMaleImage;
}

function parseDOBValue(value) {
  if (typeof value !== 'string') return { year: null, month: null, day: null };
  const parts = value.split('-');
  if (parts.length !== 3) return { year: null, month: null, day: null };
  const year = Number(parts[0]);
  const month = Number(parts[1]);
  const day = Number(parts[2]);
  if (!Number.isInteger(year) || !Number.isInteger(month) || !Number.isInteger(day)) {
    return { year: null, month: null, day: null };
  }
  return { year, month, day };
}

function toISODate(year, month, day) {
  if (!year || !month || !day) return '';
  return `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
}

function getMaxSelectableDay(year, month) {
  const limit = getDaysInMonth(year, month);
  const latestAllowed = getLatestAllowedDOBParts();
  if (year === latestAllowed.year && month === latestAllowed.month) {
    return Math.min(limit, latestAllowed.day);
  }
  return limit;
}

function getLatestAllowedDOBParts() {
  const today = new Date();
  return {
    year: today.getFullYear() - MIN_AGE_YEARS,
    month: today.getMonth() + 1,
    day: today.getDate(),
  };
}

function sanitizeYearMonthDay(year, month, day) {
  const latestAllowed = getLatestAllowedDOBParts();
  let nextYear = Number.isInteger(year) ? year : null;
  let nextMonth = Number.isInteger(month) ? month : null;
  let nextDay = Number.isInteger(day) ? day : null;

  if (nextYear && nextYear > latestAllowed.year) nextYear = latestAllowed.year;
  if (nextMonth && (nextMonth < 1 || nextMonth > 12)) nextMonth = null;

  if (nextYear && nextMonth && nextYear === latestAllowed.year && nextMonth > latestAllowed.month) {
    nextMonth = latestAllowed.month;
    nextDay = null;
  }

  if (nextYear && nextMonth && nextDay) {
    const maxDay = getMaxSelectableDay(nextYear, nextMonth);
    if (nextDay > maxDay) nextDay = null;
    if (nextDay < 1) nextDay = null;
  }

  return { year: nextYear, month: nextMonth, day: nextDay };
}

function DOBSelector({
  value = '',
  onChange,
  onMetaChange,
  gender = 'male',
}) {
  const initial = parseDOBValue(value);
  const [selectedYear, setSelectedYear] = useState(initial.year);
  const [selectedMonth, setSelectedMonth] = useState(initial.month);
  const [selectedDay, setSelectedDay] = useState(initial.day);

  useEffect(() => {
    const parsedValue = parseDOBValue(value);
    const parsed = sanitizeYearMonthDay(parsedValue.year, parsedValue.month, parsedValue.day);
    setSelectedYear(parsed.year);
    setSelectedMonth(parsed.month);
    setSelectedDay(parsed.day);
  }, [value]);

  const now = new Date();
  const latestAllowed = {
    year: now.getFullYear() - MIN_AGE_YEARS,
    month: now.getMonth() + 1,
    day: now.getDate(),
  };
  const maxSelectableYear = latestAllowed.year;
  const maxSelectableMonth = latestAllowed.month;
  const minYear = maxSelectableYear - 110;
  const years = useMemo(
    () => Array.from({ length: (maxSelectableYear - minYear) + 1 }, (_, i) => maxSelectableYear - i),
    [maxSelectableYear, minYear]
  );

  const availableMonths = useMemo(() => {
    if (!selectedYear) return MONTHS.map((name, index) => ({ month: index + 1, name }));
    const maxMonth = selectedYear === maxSelectableYear ? maxSelectableMonth : 12;
    return MONTHS.slice(0, maxMonth).map((name, index) => ({ month: index + 1, name }));
  }, [selectedYear, maxSelectableYear, maxSelectableMonth]);

  const availableDays = useMemo(() => {
    if (!selectedYear || !selectedMonth) return [];
    const maxDay = getMaxSelectableDay(selectedYear, selectedMonth);
    return Array.from({ length: maxDay }, (_, i) => i + 1);
  }, [selectedYear, selectedMonth]);

  const effectiveStep = useMemo(() => {
    if (!selectedYear) return 1;
    if (!selectedMonth) return 2;
    if (!selectedDay) return 3;
    return 3;
  }, [selectedYear, selectedMonth, selectedDay]);

  const age = useMemo(
    () => calculateAgeFromDOB(selectedYear, selectedMonth, selectedDay),
    [selectedYear, selectedMonth, selectedDay]
  );
  const previewAge = useMemo(
    () => calculatePreviewAge(selectedYear, selectedMonth, selectedDay),
    [selectedYear, selectedMonth, selectedDay]
  );
  const stage = getAgeStage(Number.isFinite(age) ? age : previewAge) || { key: 'adult', label: 'Adult', emoji: '🧠' };

  useEffect(() => {
    const normalized = sanitizeYearMonthDay(selectedYear, selectedMonth, selectedDay);
    const iso = toISODate(normalized.year, normalized.month, normalized.day);
    if (onChange) onChange(iso);
    if (onMetaChange) onMetaChange({ age, stage: getAgeStage(age) });
  }, [selectedYear, selectedMonth, selectedDay, onChange, onMetaChange, age]);

  const selectYear = (year) => {
    const normalized = sanitizeYearMonthDay(year, selectedMonth, selectedDay);
    setSelectedYear(normalized.year);
    setSelectedMonth(normalized.month);
    setSelectedDay(normalized.day);
  };

  const selectMonth = (month) => {
    const normalized = sanitizeYearMonthDay(selectedYear, month, selectedDay);
    setSelectedMonth(normalized.month);
    setSelectedDay(normalized.day);
  };

  const selectDay = (day) => {
    const normalized = sanitizeYearMonthDay(selectedYear, selectedMonth, day);
    setSelectedDay(normalized.day);
  };

  return (
    <section className="dobsel-card" aria-label="Date of birth selector">
      <div className="dobsel-left">
        <div className="dobsel-header">
          <p className="dobsel-kicker">Date of Birth</p>
          <h3 className="dobsel-title">Build Your DOB</h3>
          <p className="dobsel-subtitle">Pick year, month, and day in three quick steps (15+ only).</p>
        </div>

        <div className="dobsel-progress">
          {[1, 2, 3].map((step) => (
            <span key={step} className={effectiveStep >= step ? 'is-done' : ''}>Step {step}</span>
          ))}
        </div>

        <div className="dobsel-step-block">
          <h4>1. Select Year</h4>
          <div className="dobsel-year-list" role="listbox" aria-label="Select year">
            {years.map((year) => (
              <button
                key={year}
                type="button"
                className={`dobsel-year-chip ${selectedYear === year ? 'is-active' : ''}`}
                onClick={() => selectYear(year)}
              >
                {year}
              </button>
            ))}
          </div>
        </div>

        <div className="dobsel-step-block">
          <h4>2. Select Month</h4>
          <div className="dobsel-month-grid">
            {availableMonths.map(({ month, name }) => (
              <button
                key={month}
                type="button"
                className={`dobsel-month-chip ${selectedMonth === month ? 'is-active' : ''}`}
                onClick={() => selectMonth(month)}
                disabled={!selectedYear}
              >
                {name.slice(0, 3)}
              </button>
            ))}
          </div>
        </div>

        <div className="dobsel-step-block">
          <h4>3. Select Day</h4>
          <div className="dobsel-day-grid">
            {availableDays.map((day) => (
              <button
                key={day}
                type="button"
                className={`dobsel-day-chip ${selectedDay === day ? 'is-active' : ''}`}
                onClick={() => selectDay(day)}
                disabled={!selectedYear || !selectedMonth}
              >
                {day}
              </button>
            ))}
          </div>
        </div>
      </div>

      <aside className="dobsel-preview">
        <div className="dobsel-preview-image-wrap">
          <img
            key={`${stage.key}-${gender}`}
            className="dobsel-preview-image"
            src={getStageImage(stage.key, gender)}
            alt={`${stage.label} character`}
          />
        </div>
        <div className="dobsel-preview-meta">
          <p className="dobsel-stage">
            {stage.label} {stage.emoji}
          </p>
          <p className="dobsel-age">
            {Number.isFinite(age)
              ? `${age} years`
              : Number.isFinite(previewAge)
                ? `~${previewAge} years (estimated)`
                : 'Select full DOB'}
          </p>
          <p className="dobsel-date">
            {selectedYear && selectedMonth && selectedDay
              ? toISODate(selectedYear, selectedMonth, selectedDay)
              : 'YYYY-MM-DD'}
          </p>
        </div>
      </aside>
    </section>
  );
}

export default DOBSelector;
