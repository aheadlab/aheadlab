import { test, expect } from '@playwright/test';

test('forecast, capacity recalculation, agenda and reports', async ({ page }) => {
  const errors: string[] = []; page.on('pageerror', e => errors.push(e.message));
  await page.goto('/');
  await expect(page.getByText('Energia prevista · 48 ore', { exact: true })).toBeVisible();
  await page.screenshot({ path: 'test-results/solarcast-desktop.png', fullPage: true });
  await page.getByRole('spinbutton', { name: 'Potenza nominale · kWp', exact: true }).fill('12');
  const result = page.waitForResponse(r => r.url().endsWith('/api/forecast') && r.request().method() === 'POST');
  await page.getByRole('button', { name: 'Applica parametri', exact: true }).click();
  expect((await (await result).json()).kwp).toBe(12);
  await page.getByRole('button', { name: 'Previsione 48 ore', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Dettaglio orario', exact: true })).toBeVisible();
  await expect(page.locator('tbody tr')).toHaveCount(48);
  const download = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Esporta previsione', exact: true }).click();
  expect((await download).suggestedFilename()).toBe('solarcast-previsione.csv');
  await page.getByRole('button', { name: 'Agenda consumi', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Agenda delle fasce consigliate', exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Analisi e benchmark', exact: true }).click();
  await expect(page.getByRole('heading', { name: "Protocollo dell'esecuzione", exact: true })).toBeVisible();
  expect(errors).toEqual([]);
});

test('mobile, theme and explicit public-data consent', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/');
  await expect(page.getByText('Energia prevista · 48 ore', { exact: true })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy();
  await page.getByRole('button', { name: 'Attiva tema scuro' }).click();
  await page.screenshot({ path: 'test-results/solarcast-mobile.png', fullPage: true });
  let requests = 0;
  await page.route('**/api/forecast', route => { requests++; return route.fulfill({ status: 503, contentType: 'application/json', body: JSON.stringify({ detail: 'Rete pubblica non disponibile' }) }); });
  await page.getByRole('combobox', { name: 'Sorgente', exact: true }).selectOption('pvgis');
  await page.getByRole('button', { name: 'Applica parametri', exact: true }).click();
  expect(requests).toBe(0);
  await page.getByRole('checkbox', { name: /Autorizzo download/ }).check();
  await page.getByRole('button', { name: 'Applica parametri', exact: true }).click();
  await expect(page.getByRole('alert')).toContainText('Rete pubblica non disponibile');
  expect(requests).toBe(1);
});
