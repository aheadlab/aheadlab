import { test, expect } from '@playwright/test';

test('orders, filters, bulk selection, product detail and report', async ({ page }) => {
  const errors: string[] = []; page.on('pageerror', e => errors.push(e.message));
  await page.goto('/');
  await expect(page.getByText('Prodotti analizzati', { exact: true })).toBeVisible();
  await page.screenshot({ path: 'test-results/stocksense-desktop.png', fullPage: true });
  await page.getByRole('button', { name: 'Piano di riordino', exact: true }).click();
  await page.getByRole('checkbox', { name: 'Seleziona prodotti filtrati' }).check();
  const download = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Esporta selezionati', exact: true }).click();
  expect((await download).suggestedFilename()).toBe('stocksense-selezione.csv');
  await page.getByRole('textbox', { name: 'Cerca SKU o descrizione' }).fill('nessun-prodotto');
  await expect(page.getByRole('heading', { name: 'Nessun prodotto trovato' })).toBeVisible();
  await page.getByRole('textbox', { name: 'Cerca SKU o descrizione' }).fill('');
  await page.getByRole('button', { name: /^Dettaglio / }).first().click();
  await expect(page.getByRole('dialog')).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(page.getByRole('dialog')).toHaveCount(0);
  await page.getByRole('button', { name: 'Catalogo e previsioni', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Previsione e copertura', exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Analisi e simulazioni', exact: true }).click();
  await expect(page.getByRole('heading', { name: "Protocollo dell'esecuzione", exact: true })).toBeVisible();
  expect(errors).toEqual([]);
});

test('responsive settings, recalculation and source error', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/');
  await expect(page.getByText('Prodotti analizzati', { exact: true })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy();
  await page.getByText('Politica di riordino', { exact: true }).click();
  await page.getByRole('checkbox', { name: 'Applica parametri globali' }).check();
  await page.getByRole('spinbutton', { name: 'Lead time · giorni', exact: true }).fill('30');
  await page.getByRole('button', { name: 'Applica parametri', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Aggiorna analisi', exact: true })).toBeEnabled({ timeout: 30000 });
  await page.screenshot({ path: 'test-results/stocksense-mobile.png', fullPage: true });
  await page.route('**/api/forecast', route => route.fulfill({ status: 503, contentType: 'application/json', body: JSON.stringify({ detail: 'Dati UCI non disponibili' }) }));
  await page.getByRole('combobox', { name: 'Sorgente dati', exact: true }).selectOption('uci');
  await page.getByRole('button', { name: 'Applica parametri', exact: true }).click();
  await expect(page.getByRole('alert')).toContainText('Dati UCI non disponibili');
  await expect(page.getByText('Prodotti analizzati', { exact: true })).toBeVisible();
});
