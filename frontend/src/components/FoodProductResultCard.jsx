import React from 'react';
import { productImageUrl } from './mealTemplateVisuals';

function macroText(food) {
  const protein = food?.protein ?? '0';
  const carbs = food?.carbs ?? '0';
  const fats = food?.fats ?? '0';
  return `P ${protein} / C ${carbs} / F ${fats} per oz`;
}

function FoodProductResultCard({ food, onSelect, onAddImage, busy, imageUploading }) {
  const image = productImageUrl(food);
  const provider = food?.provider || food?.external_provider || 'local';
  const providerLabel = provider === 'open_food_facts' ? 'Open Food Facts' : provider === 'usda' ? 'USDA' : provider;
  const hasImage = Boolean(image);
  const hasPendingImage = food?.image_submission_status === 'pending';

  const handleSelect = (event) => {
    event.preventDefault();
    event.stopPropagation();
    onSelect(food);
  };

  return (
    <article className="food-product-card">
      <div className={`food-product-card__image ${hasImage ? '' : 'is-missing'}`}>
        {hasImage ? (
          <img src={image} alt="" />
        ) : (
          <div className="food-product-card__placeholder">
            <span>No product image</span>
          </div>
        )}
      </div>
      <div className="food-product-card__body">
        <div className="food-product-card__header">
          <strong>{food?.display_name || food?.name || food?.fdc_id || 'Product'}</strong>
          <span className="client-q-chip">{providerLabel}</span>
        </div>
        <div className="food-product-card__meta">
          {food?.brand_name ? <span>{food.brand_name}</span> : <span>No brand listed</span>}
          {provider === 'usda' && food?.fdc_id ? <span>FDC {food.fdc_id}</span> : null}
          {food?.barcode ? <span>UPC/GTIN {food.barcode}</span> : null}
        </div>
        <div className="food-product-card__meta">
          <span>{macroText(food)}</span>
          {food?.calories ? <span>{food.calories} cal/oz</span> : null}
        </div>
        {food?.serving_size || food?.serving_unit || food?.serving_weight_grams ? (
          <div className="food-product-card__meta">
            <span>
              Serving {food?.serving_size || '-'} {food?.serving_unit || ''}
              {food?.serving_weight_grams ? ` (${food.serving_weight_grams}g)` : ''}
            </span>
          </div>
        ) : null}
        {food?.measurement_basis_label ? (
          <div className="food-product-card__meta">
            <span>{food.measurement_basis_label}</span>
          </div>
        ) : null}
        {food?.ingredients ? (
          <div className="food-product-card__meta food-product-card__ingredients">
            <span>{food.ingredients}</span>
          </div>
        ) : null}
        {hasPendingImage ? <p className="client-q-help">Image submitted for review.</p> : null}
      </div>
      <div className="food-product-card__actions">
        <button type="button" className="client-q-btn secondary" onClick={handleSelect} disabled={busy}>
          Select
        </button>
        {!hasImage ? (
          <label className={`client-q-btn secondary food-product-card__upload ${busy || imageUploading ? 'is-disabled' : ''}`}>
            {imageUploading ? 'Uploading...' : 'Add image'}
            <input
              type="file"
              accept="image/*"
              disabled={busy || imageUploading}
              onChange={(event) => {
                const file = event.target.files?.[0];
                if (file) onAddImage(food, file);
                event.target.value = '';
              }}
            />
          </label>
        ) : null}
      </div>
    </article>
  );
}

export default FoodProductResultCard;
