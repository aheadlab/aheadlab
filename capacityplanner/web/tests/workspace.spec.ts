import {test,expect} from '@playwright/test';

test('planner, parameters, hourly export and research',async({page})=>{
  await page.goto('/');
  await expect(page.getByText('Demo sintetica · replay di 24 ore')).toBeVisible();
  await expect(page.getByRole('img',{name:'Previsione e capacità oraria'})).toBeVisible();
  await page.getByLabel('Capacità per unità').fill('300');
  await expect(page.getByText(/Parametri modificati/)).toBeVisible();
  await page.getByRole('button',{name:'Applica parametri'}).click();
  await expect(page.getByText(/Parametri modificati/)).toHaveCount(0);
  await page.getByRole('button',{name:'Piano orario',exact:true}).click();
  await expect(page.locator('tbody tr')).toHaveCount(24);
  const download=page.waitForEvent('download');
  await page.getByRole('button',{name:'Esporta CSV'}).click();
  expect((await download).suggestedFilename()).toBe('capacity-plan.csv');
  await page.getByRole('button',{name:'Risultati della ricerca',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Il modello alla prova.'})).toBeVisible();
  await expect(page.getByRole('heading',{name:'Tutti i metodi, sullo stesso test'})).toBeVisible();
  await page.screenshot({path:'test-results/research-desktop.png',fullPage:true});
});

test('real replay, dark theme and mobile',async({page})=>{
  await page.setViewportSize({width:390,height:844});
  await page.goto('/');
  await expect(page.getByText('Demo sintetica · replay di 24 ore')).toBeVisible();
  await page.getByRole('combobox',{name:'Scenario',exact:true}).selectOption('cesnet');
  await page.getByLabel('Modello di previsione').selectOption('5M');
  await page.getByRole('button',{name:'Applica parametri'}).click();
  await expect(page.locator('.source-strip')).toContainText('CESNET');
  await page.getByRole('button',{name:'Attiva tema scuro'}).click();
  await expect(page.locator('html')).toHaveAttribute('data-theme','dark');
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy();
  await page.screenshot({path:'test-results/planner-mobile.png',fullPage:true});
  await page.getByRole('button',{name:'Apri navigazione'}).click();
  await page.getByRole('button',{name:'Metodo e dati',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Dalla previsione alla decisione.'})).toBeVisible();
});

test('failed calculation keeps last applied result and offers retry',async({page})=>{
  await page.goto('/');
  await expect(page.getByText('Demo sintetica · replay di 24 ore')).toBeVisible();
  await page.route('**/api/forecast',route=>route.fulfill({status:503,contentType:'application/json',body:JSON.stringify({detail:'Modello non disponibile'})}));
  await page.getByLabel('Modello di previsione').selectOption('5M');
  await page.getByRole('button',{name:'Applica parametri'}).click();
  await expect(page.getByRole('alert')).toContainText('Modello non disponibile');
  await expect(page.locator('.source-strip')).toContainText('Settimana precedente');
  await page.unroute('**/api/forecast');
  await page.getByLabel('Modello di previsione').selectOption('daily');
  await page.getByRole('button',{name:'Riprova',exact:true}).click();
  await expect(page.getByRole('alert')).toHaveCount(0);
});
