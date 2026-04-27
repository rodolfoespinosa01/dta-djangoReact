import React from 'react';
import FoodProductResultCard from './FoodProductResultCard';

function ProductSearchPicker({
  picker,
  onClose,
  onQueryChange,
  onBarcodeChange,
  onSearch,
  onBarcodeLookup,
  onSelect,
  onAddImage,
}) {
  if (!picker?.open) return null;

  const handleClose = (event) => {
    event?.preventDefault();
    event?.stopPropagation();
    onClose();
  };

  const handleSearch = (event) => {
    event?.preventDefault();
    event?.stopPropagation();
    onSearch();
  };

  const handleBarcodeLookup = (event) => {
    event?.preventDefault();
    event?.stopPropagation();
    onBarcodeLookup();
  };

  return (
    <section className="product-picker-panel">
      <div className="product-picker-panel__top">
        <div>
          <strong>Choose specific product</strong>
          <p className="client-q-help">Optional product override for {picker.canonicalCategory}</p>
        </div>
        <button type="button" className="client-q-btn secondary" onClick={handleClose}>
          Close
        </button>
      </div>
      <div className="product-picker-panel__search">
        <label>
          Search products
          <input
            type="text"
            value={picker.query}
            onChange={(e) => onQueryChange(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                e.preventDefault();
                handleSearch(e);
              }
            }}
          />
        </label>
        <button type="button" className="client-q-btn" onClick={handleSearch} disabled={picker.loading}>
          {picker.loading ? 'Searching...' : 'Search'}
        </button>
      </div>
      <div className="product-picker-panel__search">
        <label>
          Barcode / UPC / GTIN
          <input
            type="text"
            value={picker.barcode || ''}
            inputMode="numeric"
            onChange={(e) => onBarcodeChange(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                e.preventDefault();
                handleBarcodeLookup(e);
              }
            }}
          />
        </label>
        <button type="button" className="client-q-btn secondary" onClick={handleBarcodeLookup} disabled={picker.loading}>
          Lookup barcode
        </button>
      </div>
      {picker.error ? <p className="client-q-error">{picker.error}</p> : null}
      {picker.notFound ? <p className="client-q-help">No product found for this barcode.</p> : null}
      <div className="food-product-grid">
        {(picker.results || []).map((food) => (
          <FoodProductResultCard
            key={`${food.provider || food.external_provider || 'product'}-${food.provider_product_id || food.external_food_id || food.fdc_id || food.barcode}`}
            food={food}
            canonicalCategory={picker.canonicalCategory}
            onSelect={onSelect}
            onAddImage={onAddImage}
            busy={picker.loading}
            imageUploading={picker.imageUploadingId === (food.provider_product_id || food.external_food_id || food.fdc_id || food.barcode)}
          />
        ))}
      </div>
      {!picker.loading && !(picker.results || []).length ? (
        <p className="client-q-help">Search by product name or brand, or scan/type a barcode. Product photos come from Open Food Facts when available.</p>
      ) : null}
    </section>
  );
}

export default ProductSearchPicker;
