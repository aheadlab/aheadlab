import { test, expect } from '@playwright/test';

test('report listing recovers after an HTTP error and filters rows', async ({ page }) => {
  await page.route('**/api/reports', route => route.fulfill({ status: 503, contentType: 'application/json', body: JSON.stringify({ detail: 'Report temporaneamente non disponibili' }) }));
  await page.goto('/#reports');
  await expect(page.getByRole('alert')).toContainText('Report temporaneamente non disponibili');
  await page.unroute('**/api/reports');
  await page.getByRole('button', { name: 'Riprova', exact: true }).click();
  await expect(page.getByRole('heading', { name: "Protocollo dell'esecuzione", exact: true })).toBeVisible();
  await page.getByRole('textbox', { name: 'Cerca nei risultati' }).fill('zzzz-no-matching-row');
  await expect(page.getByRole('heading', { name: 'Nessun risultato', exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Svuota ricerca', exact: true }).click();
  await expect(page.locator('tbody tr').first()).toBeVisible();
});
