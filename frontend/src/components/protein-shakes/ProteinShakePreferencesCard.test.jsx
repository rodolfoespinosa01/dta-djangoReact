import { act, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import ProteinShakePreferencesCard from './ProteinShakePreferencesCard';
import { apiRequest } from '../../api/client';

jest.mock('../../api/client', () => ({
  apiRequest: jest.fn(),
}));

const templatePayload = {
  id: 1,
  name: 'Banana Peanut Butter Protein Shake',
  slug: 'banana-peanut-butter-protein-shake',
  description: 'Protein powder with milk, banana, and peanut butter powder.',
  default_scoop_count: 1,
  ingredient_slots: [
    {
      id: 10,
      slot_key: 'protein_powder',
      display_name: 'Protein Powder',
      required: true,
      allow_user_override: true,
      allow_exclude: false,
      default_food_library_item: { id: 100, name: 'Protein Powder STANDARD', display_name: 'Protein Powder STANDARD', protein: '24', carbs: '3', fats: '2' },
      default_serving_amount: '1.0000',
      default_serving_unit: 'scoop',
      sort_order: 1,
      macro_role: 'protein',
    },
    {
      id: 11,
      slot_key: 'liquid',
      display_name: 'Liquid',
      required: false,
      allow_user_override: true,
      allow_exclude: true,
      default_food_library_item: { id: 101, name: 'Milk STANDARD', display_name: 'Milk STANDARD', protein: '8', carbs: '12', fats: '5' },
      default_serving_amount: '1.0000',
      default_serving_unit: 'cup',
      sort_order: 2,
      macro_role: 'liquid',
    },
  ],
};

const standardItems = [
  { id: 100, name: 'Protein Powder STANDARD', display_name: 'Protein Powder STANDARD', protein: '24', carbs: '3', fats: '2' },
  { id: 101, name: 'Milk STANDARD', display_name: 'Milk STANDARD', protein: '8', carbs: '12', fats: '5' },
  { id: 102, name: 'Water STANDARD', display_name: 'Water STANDARD', protein: '0', carbs: '0', fats: '0' },
];

function mockInitialLoad(extra = {}) {
  apiRequest.mockImplementation((path, options = {}) => {
    if (path === '/api/v1/users/client/app/protein-shakes/templates/') {
      return Promise.resolve({
        ok: true,
        data: {
          protein_shake_templates: [templatePayload],
          protein_shake_preferences: [],
          protein_shake_standard_items: standardItems,
        },
      });
    }
    if (path === '/api/v1/users/client/app/food-overrides/products/search/') {
      return Promise.resolve({
        ok: true,
        data: {
          products: [
            {
              provider: 'open_food_facts',
              provider_product_id: '737628064502',
              display_name: 'Brand Whey Protein',
              brand_name: 'Brand',
              protein: '24',
              carbs: '3',
              fats: '2',
            },
          ],
        },
      });
    }
    if (path === '/api/v1/users/client/app/protein-shakes/preference/') {
      return Promise.resolve({
        ok: true,
        data: {
          protein_shake_preference: {
            template_id: 1,
            template_slug: 'banana-peanut-butter-protein-shake',
            enabled: true,
            ingredient_selections: options.body?.ingredient_selections?.map((row) => ({
              ...row,
              selected_food_library_item: standardItems.find((item) => item.id === row.selected_food_library_item_id) || null,
            })) || [],
          },
        },
      });
    }
    return Promise.resolve({ ok: true, data: extra[path] || {} });
  });
}

beforeEach(() => {
  apiRequest.mockReset();
});

test('does not render when protein shake is disabled', () => {
  render(<ProteinShakePreferencesCard enabled={false} />);

  expect(screen.queryByText('Protein Shake Preferences')).not.toBeInTheDocument();
});

test('renders default template, required slot, optional exclusion, and water option without scoop controls', async () => {
  const onCompletionChange = jest.fn();
  mockInitialLoad();

  render(<ProteinShakePreferencesCard enabled onCompletionChange={onCompletionChange} />);

  expect(await screen.findByText('Banana Peanut Butter Protein Shake')).toBeInTheDocument();
  expect(screen.queryByRole('button', { name: '1 scoop' })).not.toBeInTheDocument();
  expect(screen.queryByRole('button', { name: '2 scoops' })).not.toBeInTheDocument();
  expect(screen.getByText('We’ll calculate the amount of protein powder needed based on your meal plan.')).toBeInTheDocument();
  expect(screen.getByText('Protein powder is required for this shake.')).toBeInTheDocument();
  expect(screen.getByRole('checkbox', { name: 'Exclude this ingredient' })).toBeInTheDocument();
  expect(screen.getByRole('option', { name: /Water STANDARD/ })).toBeInTheDocument();
  await waitFor(() => expect(onCompletionChange).toHaveBeenLastCalledWith(true));
});

test('can select branded protein powder and save preference payload', async () => {
  mockInitialLoad();

  render(<ProteinShakePreferencesCard enabled />);

  await screen.findByText('Banana Peanut Butter Protein Shake');
  await userEvent.click(screen.getAllByRole('button', { name: 'Search or scan product' })[0]);
  await userEvent.clear(screen.getByLabelText('Search products'));
  await userEvent.type(screen.getByLabelText('Search products'), 'whey');
  await act(async () => {
    await userEvent.click(screen.getByRole('button', { name: 'Search' }));
  });
  await userEvent.click(await screen.findByRole('button', { name: 'Select' }));
  await act(async () => {
    await userEvent.click(screen.getByRole('button', { name: 'Save Protein Shake Preferences' }));
  });
  expect(await screen.findByText('Protein shake preferences saved.')).toBeInTheDocument();

  await waitFor(() => {
    expect(apiRequest).toHaveBeenCalledWith(
      '/api/v1/users/client/app/protein-shakes/preference/',
      expect.objectContaining({
        method: 'PUT',
        body: expect.objectContaining({
          template_id: 1,
          ingredient_selections: expect.arrayContaining([
            expect.objectContaining({
              slot_key: 'protein_powder',
              external_product_data: expect.objectContaining({
                provider_product_id: '737628064502',
              }),
              excluded: false,
            }),
          ]),
        }),
      })
    );
  });
  const saveCall = apiRequest.mock.calls.find(([path]) => path === '/api/v1/users/client/app/protein-shakes/preference/');
  expect(saveCall[1].body).not.toHaveProperty('scoop_count');
});
