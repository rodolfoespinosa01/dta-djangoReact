import React, { useEffect, useMemo, useRef, useState } from 'react';
import './WeightSelector.css';

const MIN_LBS = 80;
const MAX_LBS = 400;
const DEFAULT_LBS = 180;
const STEP_LBS = 1;
const TICK_SPACING_PX = 12;
const DRAG_PX_PER_LB = 5;

export function clampWeightLbs(value) {
  const n = Number(value);
  if (!Number.isFinite(n)) return DEFAULT_LBS;
  return Math.min(MAX_LBS, Math.max(MIN_LBS, n));
}

export function lbsToKg(lbs) {
  return Number((Number(lbs) / 2.20462).toFixed(1));
}

export function kgToLbs(kg) {
  return Number(kg) * 2.20462;
}

export function normalizeWeightLbsValue(value, fallback = DEFAULT_LBS) {
  if (typeof value === 'number' && Number.isFinite(value)) return clampWeightLbs(value);
  if (typeof value === 'string' && value.trim() !== '' && Number.isFinite(Number(value))) {
    return clampWeightLbs(Number(value));
  }
  if (value && typeof value === 'object') {
    const unit = String(value.unit || 'lbs').toLowerCase();
    const raw = Number(value.value);
    if (!Number.isFinite(raw)) return clampWeightLbs(fallback);
    if (unit === 'kg') return clampWeightLbs(kgToLbs(raw));
    return clampWeightLbs(raw);
  }
  return clampWeightLbs(fallback);
}

function formatWeight(valueLbs, unit) {
  if (unit === 'kg') return `${lbsToKg(valueLbs).toFixed(1)} kg`;
  return `${Math.round(valueLbs)} lbs`;
}

function WeightSelector({
  value = DEFAULT_LBS,
  onChange,
  unit = 'lbs',
  onUnitChange,
  allowUnitToggle = false,
}) {
  const [liveLbs, setLiveLbs] = useState(normalizeWeightLbsValue(value));
  const [isDragging, setIsDragging] = useState(false);
  const dragStateRef = useRef({ pointerId: null, startX: 0, startLbs: liveLbs });
  const selectedUnit = unit === 'kg' ? 'kg' : 'lbs';

  useEffect(() => {
    if (isDragging) return;
    setLiveLbs(normalizeWeightLbsValue(value));
  }, [value, isDragging]);

  const ticks = useMemo(
    () => Array.from({ length: ((MAX_LBS - MIN_LBS) / STEP_LBS) + 1 }, (_, i) => MIN_LBS + i),
    []
  );

  const applyLiveWeight = (nextLbs, shouldEmit = true) => {
    const clamped = clampWeightLbs(nextLbs);
    setLiveLbs(clamped);
    if (shouldEmit && onChange) onChange(Math.round(clamped));
  };

  const handlePointerDown = (event) => {
    event.preventDefault();
    const pointerId = event.pointerId;
    event.currentTarget.setPointerCapture(pointerId);
    dragStateRef.current = {
      pointerId,
      startX: event.clientX,
      startLbs: liveLbs,
    };
    setIsDragging(true);
  };

  const handlePointerMove = (event) => {
    const drag = dragStateRef.current;
    if (!isDragging || drag.pointerId !== event.pointerId) return;
    const deltaX = event.clientX - drag.startX;
    const deltaLbs = deltaX / DRAG_PX_PER_LB;
    applyLiveWeight(drag.startLbs + deltaLbs);
  };

  const snapAndEndDrag = () => {
    const snapped = Math.round(liveLbs);
    setIsDragging(false);
    applyLiveWeight(snapped);
  };

  const handlePointerUp = (event) => {
    const drag = dragStateRef.current;
    if (drag.pointerId !== event.pointerId) return;
    snapAndEndDrag();
  };

  const handleKeyDown = (event) => {
    if (event.key === 'ArrowRight') {
      event.preventDefault();
      applyLiveWeight(Math.round(liveLbs) + 1);
      return;
    }
    if (event.key === 'ArrowLeft') {
      event.preventDefault();
      applyLiveWeight(Math.round(liveLbs) - 1);
    }
  };

  return (
    <section className="weightsel-card" aria-label="Weight selector">
      <div className="weightsel-header">
        <p className="weightsel-kicker">Body Weight</p>
        <h3 className="weightsel-value">{formatWeight(liveLbs, selectedUnit)}</h3>
      </div>

      {allowUnitToggle && onUnitChange ? (
        <div className="weightsel-unit-toggle" role="group" aria-label="Weight unit">
          <button
            type="button"
            className={selectedUnit === 'lbs' ? 'is-active' : ''}
            onClick={() => onUnitChange('lbs')}
          >
            lbs
          </button>
          <button
            type="button"
            className={selectedUnit === 'kg' ? 'is-active' : ''}
            onClick={() => onUnitChange('kg')}
          >
            kg
          </button>
        </div>
      ) : null}

      <div
        className="weightsel-dial"
        role="slider"
        tabIndex={0}
        aria-valuemin={MIN_LBS}
        aria-valuemax={MAX_LBS}
        aria-valuenow={Math.round(liveLbs)}
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        onPointerCancel={snapAndEndDrag}
        onKeyDown={handleKeyDown}
      >
        <div className="weightsel-dial-mask" />
        <div className={`weightsel-tick-track ${isDragging ? 'is-dragging' : 'is-snapping'}`}>
          <div
            className="weightsel-ticks"
            style={{ transform: `translateX(${-((liveLbs - MIN_LBS) * TICK_SPACING_PX)}px)` }}
          >
            {ticks.map((tickValue) => {
              const isMajor = tickValue % 10 === 0;
              const isMid = tickValue % 5 === 0;
              return (
                <div key={tickValue} className="weightsel-tick-slot">
                  <span className={`weightsel-tick ${isMajor ? 'major' : isMid ? 'mid' : 'minor'}`} />
                  {isMajor ? <span className="weightsel-tick-label">{tickValue}</span> : null}
                </div>
              );
            })}
          </div>
        </div>
        <div className="weightsel-center-indicator" aria-hidden="true" />
      </div>

      <p className="weightsel-hint">Drag left or right to adjust. Snaps to the nearest pound.</p>
    </section>
  );
}

export default WeightSelector;
