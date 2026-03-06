import React, { useEffect, useMemo, useRef, useState } from 'react';
import frontMaleSvg from '../../assets/questionnaire/2/front_male.svg';
import backMaleSvg from '../../assets/questionnaire/2/back_male.svg';
import frontFemaleSvg from '../../assets/questionnaire/2/front_female.svg';
import backFemaleSvg from '../../assets/questionnaire/2/back_female.svg';
import './BodyVisualizationSelector.css';

const MIN_HEIGHT_CM = 137;
const MAX_HEIGHT_CM = 213;
const DEFAULT_HEIGHT_CM = 178;
const BASELINE_CM = 170;

export function formatCmToFeetInches(cmValue) {
  const totalInches = Math.round(Number(cmValue || 0) / 2.54);
  const feet = Math.floor(totalInches / 12);
  const inches = Math.max(0, totalInches % 12);
  return `${feet}'${inches}"`;
}

export function normalizeHeightCmValue(value, fallback = DEFAULT_HEIGHT_CM) {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return Math.min(MAX_HEIGHT_CM, Math.max(MIN_HEIGHT_CM, Math.round(value)));
  }
  if (typeof value === 'string' && value.trim() !== '' && Number.isFinite(Number(value))) {
    const parsed = Number(value);
    return Math.min(MAX_HEIGHT_CM, Math.max(MIN_HEIGHT_CM, Math.round(parsed)));
  }
  if (value && typeof value === 'object') {
    const unit = String(value.unit || '').toLowerCase();
    if (unit === 'cm') {
      const cm = Number(value.cm);
      if (Number.isFinite(cm)) {
        return Math.min(MAX_HEIGHT_CM, Math.max(MIN_HEIGHT_CM, Math.round(cm)));
      }
    }
    const feet = Number(value.feet);
    const inches = Number(value.inches);
    if (Number.isFinite(feet) || Number.isFinite(inches)) {
      const normalizedFeet = Number.isFinite(feet) ? feet : 0;
      const normalizedInches = Number.isFinite(inches) ? inches : 0;
      const cm = (normalizedFeet * 30.48) + (normalizedInches * 2.54);
      if (Number.isFinite(cm) && cm > 0) {
        return Math.min(MAX_HEIGHT_CM, Math.max(MIN_HEIGHT_CM, Math.round(cm)));
      }
    }
  }
  return fallback;
}

function bodyImageFor(gender, view) {
  if (gender === 'female') {
    return view === 'back' ? backFemaleSvg : frontFemaleSvg;
  }
  return view === 'back' ? backMaleSvg : frontMaleSvg;
}

function bodyImageScale(gender, view) {
  // Source SVG canvases are not perfectly normalized.
  // Calibrate each variant so front/back land at a similar visual height.
  if (gender === 'male' && view === 'back') return 1.18;
  return 1.0;
}

function bodyImageOffsetY(gender, view) {
  if (gender === 'male' && view === 'back') return 6;
  return 0;
}

function BodyVisualizationSelector({
  value = DEFAULT_HEIGHT_CM,
  onChange,
  gender = 'male',
}) {
  const [markerTopPx, setMarkerTopPx] = useState(null);
  const previewRef = useRef(null);
  const figureShellRef = useRef(null);
  const heightCm = normalizeHeightCmValue(value);
  const activeGender = gender === 'female' ? 'female' : 'male';

  const visualScale = useMemo(() => {
    const ratio = heightCm / BASELINE_CM;
    const scaleY = Math.max(0.85, Math.min(1.28, ratio));
    const horizontalNudge = (scaleY - 1) * 0.2;
    const scaleX = Math.max(0.92, Math.min(1.12, 1 + horizontalNudge));
    return { scaleX, scaleY };
  }, [heightCm]);

  const onHeightInput = (event) => {
    const next = Number(event.target.value);
    if (Number.isFinite(next) && onChange) onChange(next);
  };

  useEffect(() => {
    const updateMarker = () => {
      const previewEl = previewRef.current;
      const figureEl = figureShellRef.current;
      if (!previewEl || !figureEl) return;

      const previewRect = previewEl.getBoundingClientRect();
      const figureRect = figureEl.getBoundingClientRect();
      const nextTop = figureRect.top - previewRect.top;
      setMarkerTopPx(Number.isFinite(nextTop) ? Math.max(16, nextTop) : null);
    };

    updateMarker();
    if (typeof ResizeObserver === 'undefined') return undefined;

    const ro = new ResizeObserver(() => updateMarker());
    if (previewRef.current) ro.observe(previewRef.current);
    if (figureShellRef.current) ro.observe(figureShellRef.current);
    window.addEventListener('resize', updateMarker);

    return () => {
      ro.disconnect();
      window.removeEventListener('resize', updateMarker);
    };
  }, [heightCm, activeGender, visualScale.scaleX, visualScale.scaleY]);

  return (
    <section className="bodyviz-card" aria-label="Body visualization height selector">
      <div className="bodyviz-controls">
        <div className="bodyviz-heading-group">
          <p className="bodyviz-kicker">Body Height</p>
          <h3 className="bodyviz-title">{formatCmToFeetInches(heightCm)} <span>{heightCm} cm</span></h3>
        </div>

        <p className="bodyviz-static-meta">
          Anatomy preview: {activeGender === 'female' ? 'Female' : 'Male'} (front and back)
        </p>

        <label className="bodyviz-slider-wrap">
          <div className="bodyviz-slider-label">
            <span>Height</span>
            <strong>{formatCmToFeetInches(heightCm)}</strong>
          </div>
          <input
            className="bodyviz-slider"
            type="range"
            min={MIN_HEIGHT_CM}
            max={MAX_HEIGHT_CM}
            value={heightCm}
            onChange={onHeightInput}
          />
          <div className="bodyviz-slider-range">
            <span>{MIN_HEIGHT_CM} cm</span>
            <span>{MAX_HEIGHT_CM} cm</span>
          </div>
        </label>
      </div>

      <div ref={previewRef} className="bodyviz-preview">
        <div className="bodyviz-height-axis" aria-hidden="true">
          <span className="bodyviz-axis-max">{MAX_HEIGHT_CM} cm</span>
          <span className="bodyviz-axis-min">{MIN_HEIGHT_CM} cm</span>
          <div className="bodyviz-axis-line" />
          {markerTopPx !== null ? (
            <div className="bodyviz-axis-marker" style={{ top: `${markerTopPx}px` }}>
              <span>{heightCm} cm · {formatCmToFeetInches(heightCm)}</span>
            </div>
          ) : null}
        </div>
        <div
          ref={figureShellRef}
          className="bodyviz-figure-shell"
          style={{ transform: `scale(${visualScale.scaleX}, ${visualScale.scaleY})` }}
        >
          <div className="bodyviz-figure-pair">
            <figure className="bodyviz-figure-frame">
              <img
                className="bodyviz-figure-image"
                src={bodyImageFor(activeGender, 'front')}
                alt={`${activeGender} body front view`}
                style={{
                  transform: `translateY(${bodyImageOffsetY(activeGender, 'front')}px) scale(${bodyImageScale(activeGender, 'front')})`,
                }}
              />
              <figcaption>Front</figcaption>
            </figure>
            <figure className="bodyviz-figure-frame">
              <img
                className="bodyviz-figure-image"
                src={bodyImageFor(activeGender, 'back')}
                alt={`${activeGender} body back view`}
                style={{
                  transform: `translateY(${bodyImageOffsetY(activeGender, 'back')}px) scale(${bodyImageScale(activeGender, 'back')})`,
                }}
              />
              <figcaption>Back</figcaption>
            </figure>
          </div>
        </div>
      </div>
    </section>
  );
}

export default BodyVisualizationSelector;
