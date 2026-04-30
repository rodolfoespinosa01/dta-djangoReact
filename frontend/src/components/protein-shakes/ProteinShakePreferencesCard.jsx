import React, { useEffect, useMemo, useState } from 'react';
import { apiRequest } from '../../api/client';
import ProductSearchPicker from '../ProductSearchPicker';

const SLOT_LABELS = {
  protein_powder: 'Protein Powder',
  liquid: 'Liquid',
  carb: 'Carb Source',
  fat_addin: 'Fat/Add-in',
  sweetener: 'Sweetener',
};

const EMPTY_PICKER = {
  open: false,
  slotKey: '',
  query: '',
  barcode: '',
  loading: false,
  error: '',
  results: [],
  notFound: false,
  imageUploadingId: '',
};

function decimalLabel(value, suffix = '') {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) return suffix ? `0${suffix}` : '0';
  const text = Number.isInteger(parsed) ? String(parsed) : parsed.toFixed(2).replace(/0+$/, '').replace(/\.$/, '');
  return suffix ? `${text}${suffix}` : text;
}

function itemLabel(item) {
  if (!item) return 'None';
  const name = item.display_name || item.name || 'Selected item';
  const macros = `P ${decimalLabel(item.protein)}g / C ${decimalLabel(item.carbs)}g / F ${decimalLabel(item.fats)}g`;
  return `${name} (${macros})`;
}

function productLabel(product) {
  if (!product) return '';
  const brand = product.brand_name || product.brand;
  const name = product.display_name || product.name || 'Selected product';
  return brand ? `${brand} - ${name}` : name;
}

function selectionFromPreference(preference) {
  return (preference?.ingredient_selections || []).reduce((acc, row) => {
    if (row?.slot_key) acc[row.slot_key] = row;
    return acc;
  }, {});
}

function defaultSelectionForSlot(slot) {
  return {
    slot_id: slot.id,
    slot_key: slot.slot_key,
    selected_food_library_item_id: slot.default_food_library_item?.id || null,
    selected_food_library_item: slot.default_food_library_item || null,
    selected_food_override_id: null,
    selected_food_override: null,
    external_product_data: {},
    serving_amount: slot.default_serving_amount,
    serving_unit: slot.default_serving_unit,
    excluded: false,
  };
}

function normalizeSelection(slot, savedSelection) {
  if (!savedSelection) return defaultSelectionForSlot(slot);
  return {
    ...defaultSelectionForSlot(slot),
    selected_food_library_item_id: savedSelection.selected_food_library_item?.id || null,
    selected_food_library_item: savedSelection.selected_food_library_item || null,
    selected_food_override_id: savedSelection.selected_food_override?.id || null,
    selected_food_override: savedSelection.selected_food_override || null,
    external_product_data: savedSelection.external_product_data || {},
    serving_amount: savedSelection.serving_amount || slot.default_serving_amount,
    serving_unit: savedSelection.serving_unit || slot.default_serving_unit,
    excluded: savedSelection.excluded === true,
  };
}

function standardItemsForSlot(slot, standardItems) {
  const namesBySlot = {
    protein_powder: ['Protein Powder STANDARD'],
    liquid: ['Milk STANDARD', 'Water STANDARD'],
    carb: ['Banana STANDARD'],
    fat_addin: ['Peanut Butter Powder STANDARD'],
    sweetener: ['Honey STANDARD'],
  };
  const names = namesBySlot[slot.slot_key] || [];
  const rows = standardItems.filter((item) => names.includes(item.name));
  if (slot.default_food_library_item && !rows.some((item) => item.id === slot.default_food_library_item.id)) {
    rows.unshift(slot.default_food_library_item);
  }
  return rows;
}

function ProteinShakePreferencesCard({ enabled, onCompletionChange }) {
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [templates, setTemplates] = useState([]);
  const [standardItems, setStandardItems] = useState([]);
  const [templateId, setTemplateId] = useState(null);
  const [selections, setSelections] = useState({});
  const [dirty, setDirty] = useState(false);
  const [picker, setPicker] = useState(EMPTY_PICKER);

  const selectedTemplate = useMemo(
    () => templates.find((template) => Number(template.id) === Number(templateId)) || templates[0] || null,
    [templates, templateId]
  );

  const slots = useMemo(() => (
    [...(selectedTemplate?.ingredient_slots || [])].sort((a, b) => Number(a.sort_order || 0) - Number(b.sort_order || 0))
  ), [selectedTemplate]);

  const hasRequiredFields = !enabled || Boolean(
    selectedTemplate
    && slots.some((slot) => {
      if (slot.slot_key !== 'protein_powder') return false;
      const selection = selections[slot.slot_key] || defaultSelectionForSlot(slot);
      return !selection.excluded && Boolean(
        selection.selected_food_override_id
        || selection.selected_food_library_item_id
        || selection.external_product_data?.provider_product_id
        || slot.default_food_library_item?.id
      );
    })
  );
  const isComplete = hasRequiredFields && !dirty;

  useEffect(() => {
    onCompletionChange?.(isComplete);
  }, [isComplete, onCompletionChange]);

  useEffect(() => {
    if (!enabled) return;
    let ignore = false;
    setLoading(true);
    setError('');
    apiRequest('/api/v1/users/client/app/protein-shakes/templates/', { auth: true })
      .then((res) => {
        if (ignore) return;
        if (!res.ok) {
          setError(res.data?.error?.message || 'Unable to load protein shake templates.');
          return;
        }
        const nextTemplates = Array.isArray(res.data?.protein_shake_templates) ? res.data.protein_shake_templates : [];
        const nextStandardItems = Array.isArray(res.data?.protein_shake_standard_items) ? res.data.protein_shake_standard_items : [];
        const preference = Array.isArray(res.data?.protein_shake_preferences) ? res.data.protein_shake_preferences[0] : null;
        const template = nextTemplates.find((row) => row.id === preference?.template_id) || nextTemplates[0] || null;
        const savedBySlot = selectionFromPreference(preference);
        setTemplates(nextTemplates);
        setStandardItems(nextStandardItems);
        setTemplateId(template?.id || null);
        setSelections((template?.ingredient_slots || []).reduce((acc, slot) => {
          acc[slot.slot_key] = normalizeSelection(slot, savedBySlot[slot.slot_key]);
          return acc;
        }, {}));
        setDirty(false);
      })
      .catch((err) => {
        console.error(err);
        if (!ignore) setError('Unable to load protein shake templates.');
      })
      .finally(() => {
        if (!ignore) setLoading(false);
      });
    return () => { ignore = true; };
  }, [enabled]);

  useEffect(() => {
    if (!selectedTemplate) return;
    setSelections((prev) => slots.reduce((acc, slot) => {
      acc[slot.slot_key] = prev[slot.slot_key] || defaultSelectionForSlot(slot);
      return acc;
    }, {}));
  }, [selectedTemplate, slots]);

  if (!enabled) return null;

  const updateSlot = (slot, patch) => {
    setDirty(true);
    setSelections((prev) => ({
      ...prev,
      [slot.slot_key]: {
        ...(prev[slot.slot_key] || defaultSelectionForSlot(slot)),
        ...patch,
      },
    }));
  };

  const selectStandardItem = (slot, item) => {
    updateSlot(slot, {
      selected_food_library_item_id: item?.id || null,
      selected_food_library_item: item || null,
      selected_food_override_id: null,
      selected_food_override: null,
      external_product_data: {},
      excluded: false,
    });
  };

  const openPicker = (slot) => {
    const defaultName = slot.default_food_library_item?.display_name || slot.default_food_library_item?.name || slot.display_name || '';
    setPicker({
      ...EMPTY_PICKER,
      open: true,
      slotKey: slot.slot_key,
      canonicalCategory: SLOT_LABELS[slot.slot_key] || slot.display_name,
      query: defaultName.replace(/\sSTANDARD$/i, ''),
    });
  };

  const searchProducts = async () => {
    const query = String(picker.query || '').trim();
    if (!query) return;
    setPicker((prev) => ({ ...prev, loading: true, error: '', notFound: false }));
    try {
      const res = await apiRequest('/api/v1/users/client/app/food-overrides/products/search/', {
        method: 'POST',
        auth: true,
        body: { query, page: 1, page_size: 12, providers: ['open_food_facts', 'usda'] },
      });
      if (!res.ok) {
        setPicker((prev) => ({ ...prev, loading: false, error: 'Could not search products right now. Try again.' }));
        return;
      }
      setPicker((prev) => ({ ...prev, loading: false, results: Array.isArray(res.data?.products) ? res.data.products : [] }));
    } catch (err) {
      console.error(err);
      setPicker((prev) => ({ ...prev, loading: false, error: 'Could not search products right now. Try again.' }));
    }
  };

  const lookupBarcode = async () => {
    const barcode = String(picker.barcode || '').trim();
    if (!barcode) return;
    setPicker((prev) => ({ ...prev, loading: true, error: '', notFound: false }));
    try {
      const res = await apiRequest('/api/v1/users/client/app/food-overrides/products/barcode/', {
        method: 'POST',
        auth: true,
        body: { barcode },
      });
      if (!res.ok) {
        setPicker((prev) => ({ ...prev, loading: false, notFound: res.status === 404, error: res.status === 404 ? '' : 'Could not search products right now. Try again.' }));
        return;
      }
      setPicker((prev) => ({ ...prev, loading: false, results: res.data?.product ? [res.data.product] : [] }));
    } catch (err) {
      console.error(err);
      setPicker((prev) => ({ ...prev, loading: false, error: 'Could not search products right now. Try again.' }));
    }
  };

  const selectProduct = (product) => {
    const slot = slots.find((row) => row.slot_key === picker.slotKey);
    if (!slot) return;
    const productId = product?.provider_product_id || product?.external_food_id || product?.fdc_id || product?.barcode;
    updateSlot(slot, {
      selected_food_library_item_id: null,
      selected_food_library_item: null,
      selected_food_override_id: null,
      selected_food_override: null,
      external_product_data: {
        ...product,
        provider_product_id: productId,
      },
      excluded: false,
    });
    setPicker(EMPTY_PICKER);
  };

  const uploadProductImage = async (food, file) => {
    const providerProductId = food?.provider_product_id || food?.external_food_id || food?.fdc_id || food?.barcode;
    const provider = food?.provider || food?.external_provider || (food?.fdc_id ? 'usda' : '');
    if (!providerProductId || !provider || !file) return;
    const formData = new FormData();
    formData.append('provider', provider);
    formData.append('provider_product_id', providerProductId);
    formData.append('barcode', food?.barcode || '');
    formData.append('product_name', food?.display_name || food?.name || '');
    formData.append('brand', food?.brand_name || food?.brand || '');
    formData.append('image', file);
    setPicker((prev) => ({ ...prev, imageUploadingId: providerProductId, error: '' }));
    try {
      const res = await apiRequest('/api/v1/users/client/app/food-overrides/products/images/submit/', {
        method: 'POST',
        auth: true,
        body: formData,
      });
      if (!res.ok) {
        setPicker((prev) => ({ ...prev, imageUploadingId: '', error: 'Could not upload image right now. Try again.' }));
        return;
      }
      const submission = res.data?.image_submission;
      setPicker((prev) => ({
        ...prev,
        imageUploadingId: '',
        results: (prev.results || []).map((row) => {
          const rowId = row.provider_product_id || row.external_food_id || row.fdc_id || row.barcode;
          if (rowId !== providerProductId || (row.provider || row.external_provider) !== provider) return row;
          return { ...row, image_submission_status: submission?.status || 'pending', image_submission_id: submission?.id || row.image_submission_id };
        }),
      }));
    } catch (err) {
      console.error(err);
      setPicker((prev) => ({ ...prev, imageUploadingId: '', error: 'Could not upload image right now. Try again.' }));
    }
  };

  const savePreference = async () => {
    if (!selectedTemplate) {
      setError('Choose a protein shake template first.');
      return false;
    }
    if (!hasRequiredFields) {
      setError('Protein powder is required.');
      return false;
    }
    setSaving(true);
    setError('');
    setMessage('');
    try {
      const payload = {
        template_id: selectedTemplate.id,
        enabled: true,
        ingredient_selections: slots.map((slot) => {
          const selection = selections[slot.slot_key] || defaultSelectionForSlot(slot);
          return {
            slot_id: slot.id,
            slot_key: slot.slot_key,
            selected_food_library_item_id: selection.excluded ? null : selection.selected_food_library_item_id,
            selected_food_override_id: selection.excluded ? null : selection.selected_food_override_id,
            external_product_data: selection.excluded ? {} : (selection.external_product_data || {}),
            serving_amount: selection.serving_amount || slot.default_serving_amount,
            serving_unit: selection.serving_unit || slot.default_serving_unit,
            excluded: selection.excluded === true,
          };
        }),
      };
      const res = await apiRequest('/api/v1/users/client/app/protein-shakes/preference/', {
        method: 'PUT',
        auth: true,
        body: payload,
      });
      if (!res.ok) {
        setError(res.data?.error?.message || 'Unable to save protein shake preferences.');
        return false;
      }
      const saved = res.data?.protein_shake_preference;
      if (saved) {
        const savedBySlot = selectionFromPreference(saved);
        setSelections(slots.reduce((acc, slot) => {
          acc[slot.slot_key] = normalizeSelection(slot, savedBySlot[slot.slot_key]);
          return acc;
        }, {}));
      }
      setDirty(false);
      setMessage('Protein shake preferences saved.');
      return true;
    } catch (err) {
      console.error(err);
      setError('Network error while saving protein shake preferences.');
      return false;
    } finally {
      setSaving(false);
    }
  };

  const renderSlot = (slot) => {
    const selection = selections[slot.slot_key] || defaultSelectionForSlot(slot);
    const standardOptions = standardItemsForSlot(slot, standardItems);
    const selectedStandardId = selection.selected_food_library_item_id || '';
    const selectedProduct = selection.selected_food_override || selection.external_product_data;
    return (
      <div key={slot.slot_key} className="client-q-stack" style={{ border: '1px solid rgba(20,40,74,0.1)', borderRadius: 12, padding: '0.75rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: '0.75rem', flexWrap: 'wrap' }}>
          <div>
            <strong>{SLOT_LABELS[slot.slot_key] || slot.display_name}</strong>
            <p className="client-q-help" style={{ margin: '0.25rem 0 0' }}>
              Default: {itemLabel(slot.default_food_library_item)}
            </p>
          </div>
          <span className={`client-q-chip ${slot.required ? 'warn' : ''}`}>{slot.required ? 'Required' : 'Optional'}</span>
        </div>

        {slot.allow_exclude && !slot.required ? (
          <label style={{ display: 'flex', alignItems: 'center', gap: '0.45rem' }}>
            <input
              type="checkbox"
              checked={selection.excluded === true}
              onChange={(e) => updateSlot(slot, { excluded: e.target.checked })}
            />
            Exclude this ingredient
          </label>
        ) : null}

        {slot.required ? <p className="client-q-help">Protein powder is required for this shake.</p> : null}

        {!selection.excluded ? (
          <>
            {standardOptions.length ? (
              <label>
                Standard option
                <select
                  value={selectedStandardId}
                  onChange={(e) => {
                    const item = standardOptions.find((row) => String(row.id) === e.target.value) || null;
                    selectStandardItem(slot, item);
                  }}
                >
                  <option value="">Use template default</option>
                  {standardOptions.map((item) => (
                    <option key={`${slot.slot_key}-standard-${item.id}`} value={item.id}>
                      {itemLabel(item)}
                    </option>
                  ))}
                </select>
              </label>
            ) : null}

            <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', alignItems: 'center' }}>
              {slot.allow_user_override ? (
                <button type="button" className="client-q-btn secondary" onClick={() => openPicker(slot)}>
                  Search or scan product
                </button>
              ) : null}
              {selectedProduct?.display_name || selectedProduct?.name ? (
                <>
                  <span className="client-q-chip ok">{productLabel(selectedProduct)}</span>
                  <button
                    type="button"
                    className="client-q-btn secondary"
                    onClick={() => updateSlot(slot, { external_product_data: {}, selected_food_override_id: null, selected_food_override: null })}
                  >
                    Remove product
                  </button>
                </>
              ) : null}
            </div>

            <div className="client-q-inline-grid">
              <label>
                Serving amount
                <input
                  type="number"
                  min="0"
                  step="0.25"
                  value={selection.serving_amount || ''}
                  onChange={(e) => updateSlot(slot, { serving_amount: e.target.value })}
                />
              </label>
              <label>
                Serving unit
                <input
                  type="text"
                  value={selection.serving_unit || ''}
                  onChange={(e) => updateSlot(slot, { serving_unit: e.target.value })}
                />
              </label>
            </div>
          </>
        ) : (
          <p className="client-q-help">This ingredient will be left out of your shake preference.</p>
        )}
      </div>
    );
  };

  return (
    <div className="client-q-stack" aria-label="Protein shake preferences">
      <ProductSearchPicker
        picker={picker}
        onClose={() => setPicker(EMPTY_PICKER)}
        onQueryChange={(query) => setPicker((prev) => ({ ...prev, query }))}
        onBarcodeChange={(barcode) => setPicker((prev) => ({ ...prev, barcode }))}
        onSearch={searchProducts}
        onBarcodeLookup={lookupBarcode}
        onSelect={selectProduct}
        onAddImage={uploadProductImage}
      />

      <div className="food-pref-intro">
        <div>
          <h2>Protein Shake Preferences</h2>
          <p>Choose the exact ingredients for the shake meal reserved by your questionnaire.</p>
        </div>
        <div className="food-pref-progress">
          <span className={`client-q-chip ${isComplete ? 'ok' : 'warn'}`}>
            {isComplete ? 'Ready' : dirty ? 'Unsaved changes' : 'Needs protein powder'}
          </span>
        </div>
      </div>

      {loading ? <p className="client-q-help">Loading protein shake templates...</p> : null}
      {error ? <p className="client-q-error">{error}</p> : null}
      {message ? <p className="client-q-message">{message}</p> : null}

      {!loading && selectedTemplate ? (
        <>
          <div className="client-q-stack" style={{ border: '1px solid rgba(20,40,74,0.1)', borderRadius: 12, padding: '0.75rem' }}>
            <strong>{selectedTemplate.name}</strong>
            <p className="client-q-help">{selectedTemplate.description}</p>
            <p className="client-q-help">We’ll calculate the amount of protein powder needed based on your meal plan.</p>
          </div>

          <div className="client-q-stack">
            {slots.map(renderSlot)}
          </div>

          <button type="button" className="client-q-btn" onClick={savePreference} disabled={saving || !hasRequiredFields}>
            {saving ? 'Saving...' : 'Save Protein Shake Preferences'}
          </button>
        </>
      ) : null}

      {!loading && !selectedTemplate ? (
        <p className="client-q-error">No active protein shake templates are available yet.</p>
      ) : null}
    </div>
  );
}

export default ProteinShakePreferencesCard;
