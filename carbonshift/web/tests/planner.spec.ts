import {test,expect} from '@playwright/test';
test('replay applies constraints, exports and retains result after an error',async({page})=>{
 await page.goto('/');await expect(page.getByText('Guarda le ore scelte')).toBeVisible();
 await page.getByLabel('Durata',{exact:true}).selectOption('8');await page.getByLabel('Scadenza',{exact:true}).selectOption('24');
 await expect(page.getByText('Modifiche da applicare')).toBeVisible();
 await page.getByRole('button',{name:'Confronta gli orari'}).click();await expect(page.getByText('Scenario esplorativo:',{exact:false})).toBeVisible();
 const response=page.waitForResponse(r=>r.url().endsWith('/api/export'));await page.getByRole('button',{name:'Esporta CSV'}).click();
 expect((await response).status()).toBe(200);
 await page.route('**/api/plan',route=>route.fulfill({status:503,contentType:'application/json',body:JSON.stringify({detail:'Errore controllato'})}));
 await page.getByRole('button',{name:'Confronta gli orari'}).click();await expect(page.getByRole('alert')).toContainText('Errore controllato');
 await expect(page.getByText('Guarda le ore scelte')).toBeVisible();
 await page.unroute('**/api/plan');await page.reload();await expect(page.getByText('Guarda le ore scelte')).toBeVisible();
 await page.screenshot({path:'test-results/planner-desktop.png',fullPage:true});
});
test('research distinguishes the recent inconclusive check and validates CSV',async({page})=>{
 await page.goto('/');await page.getByRole('button',{name:'Le prove',exact:true}).click();
 await expect(page.getByText('Beneficio piccolo, positivo nel test storico')).toBeVisible();
 await page.getByRole('button',{name:'Controllo 2026',exact:true}).click();await expect(page.getByText('Non conclusivo sul periodo più recente')).toBeVisible();
 await page.getByRole('button',{name:'I tuoi dati',exact:true}).click();
 await page.getByLabel('Carica CSV orario').setInputFiles({name:'bad.csv',mimeType:'text/csv',buffer:Buffer.from('wrong,header\n1,2')});
 await expect(page.getByRole('alert')).toContainText('Intestazione richiesta');
 await expect(page.getByRole('button',{name:'Calcola in locale'})).toBeDisabled();
});
test('mobile and dark theme remain usable',async({page})=>{
 await page.setViewportSize({width:390,height:844});await page.goto('/');
 await expect(page.getByText('Guarda le ore scelte')).toBeVisible();
 expect(await page.evaluate(()=>document.documentElement.scrollWidth)).toBeLessThanOrEqual(391);
 await page.getByRole('button',{name:'Cambia tema'}).click();await expect(page.locator('html')).toHaveAttribute('data-theme','dark');
 await page.reload();await expect(page.locator('html')).toHaveAttribute('data-theme','dark');
 expect(await page.locator('html').evaluate(el=>getComputedStyle(el).backgroundColor)).toBe('rgb(23, 35, 29)');
 expect(await page.locator('body').evaluate(el=>getComputedStyle(el).color)).toBe('rgb(226, 233, 220)');
 await page.screenshot({path:'test-results/planner-mobile-dark.png',fullPage:true});
});
