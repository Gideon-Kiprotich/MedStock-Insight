import type { Medicine } from '../types/api';

export const medicineLabel = (medicine: Pick<Medicine, 'generic_name' | 'strength' | 'dosage_form'>): string =>
  [medicine.generic_name, [medicine.strength, medicine.dosage_form].filter(Boolean).join(' ')].filter(Boolean).join(' — ');
