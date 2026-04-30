import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useState } from 'react';

import ProteinShakeSelector from './ProteinShakeSelector';

const weekDays = ['sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday'];

function mealSchedule(defaultMeals = 5, overrides = {}, mode = 'same') {
  return {
    mode,
    default_meals: defaultMeals,
    days: weekDays.reduce((acc, day) => {
      acc[day] = overrides[day] || defaultMeals;
      return acc;
    }, {}),
  };
}

function Harness({ initialValue, meals = mealSchedule(5), training = { monday: 'before_meal_3' }, onChange }) {
  const [value, setValue] = useState(initialValue);
  return (
    <ProteinShakeSelector
      value={value}
      mealSchedule={meals}
      trainingSchedule={training}
      onChange={(nextValue) => {
        setValue(nextValue);
        onChange?.(nextValue);
      }}
    />
  );
}

test('same-mode Other excludes pre and post workout shake meals', async () => {
  render(
    <Harness
      initialValue={{
        enabled: true,
        schedule_mode: 'same',
        default_timing: 'other',
        default_selected_meal: 2,
      }}
      meals={mealSchedule(4)}
      training={{ monday: 'before_meal_2' }}
    />
  );

  expect(screen.getByRole('button', { name: 'Other' })).toHaveClass('is-active');
  expect(screen.queryByRole('button', { name: 'Meal 1' })).not.toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'Meal 2' })).toBeInTheDocument();
  expect(screen.queryByRole('button', { name: 'Meal 3' })).not.toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'Meal 4' })).toBeInTheDocument();
  expect(screen.getAllByText('Shake: Meal 2').length).toBeGreaterThan(0);

  await userEvent.click(screen.getByRole('button', { name: 'Meal 4' }));

  expect(screen.getAllByText('Shake: Meal 4').length).toBeGreaterThan(0);
});

test('custom-by-day Other uses each day meal count for manual choices', async () => {
  render(
    <Harness
      initialValue={{
        enabled: true,
        schedule_mode: 'custom',
        days: {
          monday: { enabled: true, timing: 'other', selected_meal: 3 },
          tuesday: { enabled: true, timing: 'other', selected_meal: 1 },
        },
      }}
      meals={mealSchedule(5, { monday: 4, tuesday: 6 }, 'custom')}
      training={{ monday: 'before_meal_1', tuesday: 'before_meal_6' }}
    />
  );

  const monday = screen.getByLabelText('Monday protein shake timing');
  expect(within(monday).queryByRole('button', { name: 'Meal 1' })).not.toBeInTheDocument();
  expect(within(monday).queryByRole('button', { name: 'Meal 2' })).not.toBeInTheDocument();
  expect(within(monday).getByRole('button', { name: 'Meal 3' })).toBeInTheDocument();
  expect(within(monday).getByRole('button', { name: 'Meal 4' })).toBeInTheDocument();

  const tuesday = screen.getByLabelText('Tuesday protein shake timing');
  expect(within(tuesday).getByRole('button', { name: 'Meal 1' })).toBeInTheDocument();
  expect(within(tuesday).getByRole('button', { name: 'Meal 4' })).toBeInTheDocument();
  expect(within(tuesday).queryByRole('button', { name: 'Meal 5' })).not.toBeInTheDocument();
  expect(within(tuesday).queryByRole('button', { name: 'Meal 6' })).not.toBeInTheDocument();
});

test('switching from post-workout to Other stops forcing the training-derived meal', async () => {
  render(
    <Harness
      initialValue={{
        enabled: true,
        schedule_mode: 'same',
        default_timing: 'post_workout',
        default_selected_meal: 4,
      }}
      meals={mealSchedule(4)}
      training={{ monday: 'before_meal_2' }}
    />
  );

  expect(screen.getAllByText('Shake: Meal 3').length).toBeGreaterThan(0);

  await userEvent.click(screen.getByRole('button', { name: 'Other' }));

  expect(screen.getByRole('button', { name: 'Meal 4' })).toHaveClass('is-active');
  expect(screen.getAllByText('Shake: Meal 4').length).toBeGreaterThan(0);
});

test('Other includes all meals when no training exists', () => {
  render(
    <Harness
      initialValue={{
        enabled: true,
        schedule_mode: 'same',
        default_timing: 'other',
        default_selected_meal: 1,
      }}
      meals={mealSchedule(4)}
      training={{}}
    />
  );

  for (let mealNumber = 1; mealNumber <= 4; mealNumber += 1) {
    expect(screen.getByRole('button', { name: `Meal ${mealNumber}` })).toBeInTheDocument();
  }
});
