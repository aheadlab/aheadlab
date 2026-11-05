import { test, expect } from '@playwright/test';

test('forecast, service navigation, theme persistence and CSV', async ({ page }) => {
  const errors: string[] = []; page.on('pageerror', e => errors.push(e.message));
  await page.goto('/');
  await expect(page.getByText('Speso nel mese', { exact: true })).toBeVisible();
  await page.screenshot({ path: 'test-results/cloudguard-desktop.png', fullPage: true });
  await page.getByRole('button', { name: 'Costi per servizio', exact: true }).click();
  await page.getByRole('textbox', { name: 'Cerca servizio', exact: true }).fill('RDS');
  await expect(page.getByRole('button', { name: 'Apri previsione', exact: true })).toHaveCount(1);
  await page.getByRole('button', { name: 'Apri previsione', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Previsione · Amazon RDS', exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Attiva tema scuro' }).click();
  await page.reload();
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');
  await expect(page.getByRole('heading', { name: 'Previsione · Amazon RDS', exact: true })).toBeVisible();
  const download = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Esporta previsione', exact: true }).click();
  expect((await download).suggestedFilename()).toBe('cloudguard-previsione.csv');
  await page.getByRole('button', { name: 'Centro anomalie', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Registro anomalie', exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Analisi e benchmark', exact: true }).click();
  await expect(page.getByRole('heading', { name: "Protocollo dell'esecuzione", exact: true })).toBeVisible();
  expect(errors).toEqual([]);
});

test('responsive navigation and recoverable API failure', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.route('**/api/forecast', route => route.fulfill({ status: 503, contentType: 'application/json', body: JSON.stringify({ detail: 'Modello non disponibile' }) }));
  await page.goto('/');
  await expect(page.getByRole('alert')).toContainText('Modello non disponibile');
  await page.unroute('**/api/forecast');
  await page.getByRole('button', { name: 'Riprova', exact: true }).click();
  await expect(page.getByText('Speso nel mese', { exact: true })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy();
  await page.getByRole('button', { name: 'Apri navigazione' }).click();
  await page.getByRole('button', { name: 'Centro anomalie', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Registro anomalie', exact: true })).toBeVisible();
  await page.screenshot({ path: 'test-results/cloudguard-mobile.png', fullPage: true });
});
