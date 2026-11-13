# Changelog

## Unreleased

### Changed
- The admin side is a page of the app itself (`/admin`), reached by signing in on the normal sign-in page. The
  separate admin app on its own address (port 5175 / 8081) is gone.
- The main admin account is `Admin@defake.com`, made when the server starts. Only an admin can make another admin
  (by adding an account as an admin); *Make admin* / *Remove admin* and `scripts/admin_accounts.py` are gone.

### Added
- A conclusion on every report, as the review panel asked: "Based on the reviews of this product, it looks okay to
  buy / opinions are mixed / think twice / we advise against buying it", with the reviewers' positive and negative
  share. It follows the verdict (a safety warning is never "okay to buy", however happy the reviews) and says it is a
  guide, not proof. Worked out when the report is opened from the saved result, so nothing is re-analysed.
- Products are placed in one of 39 categories from their title, in 10 groups: electronics (phone, laptop, tablet, audio,
  charger or cable, power bank, smartwatch, camera, gaming, TV, computer parts, smart home, accessory), home and living
  (appliances, kitchen, furniture, decor and lighting, cleaning, textiles, garden), fashion (clothes, shoes, bags,
  jewellery), beauty and health, baby and toys, sports, pets, food, automotive and tools, and office and media. A word
  that is a complaint for one kind of product is not for another. A category only changes what the checker does when it
  has a file in `lexicons/categories/`; so far "manipis" and "too thin" are no longer a poor-quality flag on a phone,
  laptop, tablet, computer keyboard or mouse, TV, power bank or smartwatch, but
  still are beside a part or material ("manipis na plastic", "manipis ang cable") and on everything else. The lists
  are one file per category in `lexicons/categories/`. Saved products are re-analysed once (model version `+pc1`).
- Safety rules s5: fire ("ignites a fire", "caught fire"), melting wires or cables, a swollen or bloated battery and a
  misspelt "short circuit" are now flagged; "grounded po ang cord" (a grounded plug) no longer reads as an electric
  shock; "sunog siya kanina" is no longer read as burnt rice ("kanin" matched the start of "kanina"). Checked on the
  10,000-review pool: 8 reviews change (6 added, 2 removed), none by accident, and the 300 labelled reviews are unchanged.
- The admin can add an account (name, email, password, shopper or admin) from the Manage accounts tab.
- The landing page's header shows an Admin button while the admin is signed in.

## 1.4.0 - 2026-11-01

### Added
- A new first screen: a scrolling collage of product photos behind the logo, with an Explore button.
- A sign-in page (`/enter`): one form for everyone (admin accounts go to the admin app, shoppers to the app),
  sign-up, and "Enter without signing in" to the original app.
- The original app's Home, History, Wishlist, About and FAQ are one scrolling page; the side menu is floating
  icons that scroll between the parts, and Settings is in the top bar.

### Changed
- Home is tidier: a centred welcome on the page texture, one wider link box, soft panels for each part.
- The original app's own campus-photo splash screen is removed.

## 1.3.0 - 2026-10-31

### Changed
- New brand colours: deep navy blue (main buttons, links, switches, scan progress, focus ring) and burnt mustard
  yellow (logo check mark; decoration only, never a verdict, count or warning).
- Dark mode uses a brighter navy so it passes the colour-blind distance check against the "no warnings" teal.
- `npm run check:colors` passes for light and dark.

### Earlier in this app
- Separate admin app replacing the DTI view (402956d).
- DTI view: filters, printable reports and charts (e29c748).
- Public deployment layer, browser extension and UI/UX pass (04ee1a0).
