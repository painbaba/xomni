# Indian Insurer Unclaimed-Amount Probe Matrix (Aug 2026)

Sweep of every insurer URL from the IRDAI Bima Bharosa master directory
(https://bimabharosa.irdai.gov.in/Home/UnclaimedAmount), probed 2026-08-08.
Result of probing: bulk-file publisher, search-only portal, or unreachable.

Legend: BULK = publishes downloadable unclaimed list; SEARCH = lookup form only (no bulk list); ERR = blocked/unreachable (Akamai 403, timeout, DNS).

## Life insurers

| Insurer | Unclaimed URL | Result |
|---|---|---|
| Acko Life | acko.com/life/unclaimed-amount | BULK (already collected) |
| Aditya Birla SunLife | lifeinsuranceservicing.adityabirlacapital.com/pre-unclaim | SEARCH |
| Ageas Federal | ageasfederal.com/unclaimed-payouts | SEARCH (name/DOB/policy/PAN form; "Unclaimed Payout Form" is a claim form, not a list) |
| Aviva | online.avivaindia.com/econnect/Pages/IRDA_Claims.aspx | SEARCH (data as on 31 Mar 2026) |
| Axis Max Life | maxlifeinsurance.com/cs/unclaimed-amount | SEARCH (JS) |
| Bajaj Life | life.bajajallianz.com/lifeinsurance/lifeProds/unclaimed.jsp | ERR (503/timeout) |
| Bandhan Life | aegonlife.com/unclaimed-amount-status | ERR (timeout) |
| Bharti AXA Life | bhartiaxa.com/unclaimed-amount | SEARCH |
| Canara HSBC Life | canarahsbclife.com/customer-service/claims/unclaimed-amount | SEARCH (also SCWF page) |
| Edelweiss Life | edelweisslife.in/unclaimedamount | SEARCH ("No Found Record" search) |
| Exide Life (now HDFC Life) | hdfclife.com/.../unclaimed-policyholder-payment-dues-amount-disclosure/eli | SEARCH |
| Generali Central Life | generalicentrallife.com/customer-service/unclaimed-amount | SEARCH (empty reply) |
| HDFC Life | hdfclife.com/customer-service/claims/unclaimed-policyholder-payment-dues-amount-disclosure | SEARCH (name/DOB/PAN/policy form; updated half-yearly) |
| ICICI Prudential | customer.iciciprulife.com/csr/unclaimedAmountAuthentication.htm | SEARCH (policy/PAN/email/mobile/name) |
| IndiaFirst Life | indiafirstlife.com/unclaimed-amount | **BULK PDF**: /content/dam/ifliwebsite/unclaimed-amount/unclaimed-amount.pdf — "UNCLAIMED CASES - For Period 10 years & Above", 23 pages, ~992 records (Sl No, Policy/Member id, Name, Amount, Due date) |
| IndusInd Nippon | indusindnipponlife.com/unclaimed-amount-of-policy-holders | SEARCH (also SCWF section) |
| Kotak Life | customer.kotaklifeinsurance.com/CP/customerunclaimamount.aspx | SEARCH; commented-out link to /CP/Reports/UnclaimedReport.aspx (10+ yrs) — URL exists but errors without session |
| LIC | merchant.licindia.in .../UnclaimedPolicyDues | SEARCH (already collected) |
| PNB MetLife | customerportal.pnbmetlife.com/unclaimed/amount/ | SEARCH (choose Individual/Organization → form) |
| Pramerica | pramericalife.in/unclaimed-amount | SEARCH |
| Sahara India Life | saharalife.com/vs/FrmDispUnclaimed.aspx | ERR (86-byte reply) |
| SBI Life | sbilife.co.in/unclaimed-amount-disclosure | SEARCH (min 2 of: PAN/policy/name/DOB) |
| Shriram Life | shriramlife.in/SLP/unclaimedamount → shriramlife.com/services/unclaimed-amounts | SEARCH |
| Star Union Dai-ichi | sudlife.in/public-disclosures/unclaimed-amount | ERR (Akamai 403) |
| Tata AIA | myinsurance.tataaia.com/portfolio/policy/unclaimed-funds/authenticate | SEARCH |

## General insurers

| Insurer | Unclaimed URL | Result |
|---|---|---|
| Acko General | acko.com/gi/unclaimed-amount | BULK (already collected) |
| Agriculture Insurance Co (AIC) | aicofindia.com/regulatory-compliance | ERR (JS app, no unclaimed content found) |
| Bajaj General | general.bajajallianz.com/BagicNxt/unClaimedData/searchDetails.do | SEARCH |
| Chola MS | cholainsurance.com/unclaimed-amount | SEARCH |
| ECGC | main.ecgc.in/english/public-disclosures | BULK (already collected) |
| Generali Central GI (Future Generali) | general.futuregenerali.in/... (DNS dead); generali.co.in/customer-service/unclaimed-amount | SEARCH (generali.co.in works) |
| Go Digit | godigit.com/claim/check-unclaimed-amount | SEARCH |
| HDFC ERGO | hdfcergo.com/claim/trackclaim_refund_payment_status | ERR (404) |
| ICICI Lombard | ilhc.icicilombard.com/Home/UnclaimedAmount | SEARCH (min 2 fields) |
| IFFCO Tokio | iffcotokio.co.in/claims/unclaimed-amount-policy-holders | SEARCH (page says "if you find your name in the Unclaimed Amount list" but only exposes search + request-letter PDF) |
| Kshema | kshema.co/unclaimed-amount/ | SEARCH |
| Liberty GI | libertyinsurance.in/products/irdai/irdaiindex | BULK (already collected) |
| Magma | magmainsurance.com/unclaimed-amount | SEARCH (any 2 of name/policy/DOB/PAN/customer id/receipt) |
| National Insurance | payments.nic.co.in:8443/StatusChecker/ | ERR (404) |
| Navi | navi.com/insurance/unclaimed-claims | SEARCH |
| New India Assurance | newindia.co.in/portal/unclaimedPolHolAmt | SEARCH (JS app) |
| Oriental | orientalinsurance.org.in/unclaimed-amount | ERR (tiny page) |
| Raheja QBE | rahejaqbe.com/unclaimed-amount | SEARCH |
| Reliance GI → IndusInd Insurance | indusindinsurance.com/Insurance/About-Us/Unclaimed-Amount.aspx | SEARCH ("Unclaimed Amount of Policyholder's list as on 31st MARCH 2026" heading but only search form) |
| Royal Sundaram | royalsundaram.in/app/unclaimed-amount-search | ERR (Akamai 403) |
| SBI General | sbigeneral.in/unclaimed-policy-details | SEARCH (empty reply) |
| Shriram General | serviceapi.shriramgi.net/cloud/?module=ucasearch | ERR (DNS) |
| Tata AIG | tataaig.com/service/unclaimed-amount | SEARCH (empty reply) |
| United India | portal.uiic.in/CUSTOMERPORTAL/unclaimed_query.jsp | ERR (timeout) |
| Universal Sompo | universalsompo.com/public-disclosure | SEARCH — has 3 unclaimed sub-pages (claim_refund.aspx, Refund_Data.aspx, unclaim_RefundData.aspx) all search forms; third shows "Data Not Available !!" |
| Zuno | hizuno.com/unclaimed-amount | SEARCH |
| Zurich Kotak GI | kotakgeneral.com/claims/unclaimed-amount | SEARCH (tiny reply) |

## Health insurers

| Insurer | Unclaimed URL | Result |
|---|---|---|
| Aditya Birla Health | adityabirlacapital.com/healthinsurance/unclaimed-amount | SEARCH |
| Care Health | careinsurance.com/unclaimed-amount.php | ERR (Akamai 403) |
| Manipal Cigna | manipalcigna.com/disclosures/unclaimed-amount | SEARCH (name/DOB/proposal/PAN + empty results table) |
| Narayana Health | narayanahealth.insurance/disclosures/ | SEARCH (no unclaimed section) |
| Niva Bupa | transactions.nivabupa.com/unclaimed/unclaimedamount.aspx | SEARCH |
| Star Health | starhealth.in/claim-proposal/ | ERR (timeout) |

## Search-engine notes (Aug 2026)

- Bing RSS (`curl -s "https://www.bing.com/search?q=...&format=rss" -A "<browser UA>"`):
  returned completely unrelated junk items (YouTube help, zhihu, games) for all 4 prescribed
  queries. site: operators ignored. Do not rely on it for this class.
- DuckDuckGo HTML (html.duckduckgo.com/html/?q=...) worked once then started returning a
  challenge page. The one successful query surfaced bimabharosa/Home/UnclaimedAmountsQuery,
  godigit, shriramlife, indusindinsurance.
- Google site-search via DDG is equally unreliable here; direct registry probing is the
  durable approach.
