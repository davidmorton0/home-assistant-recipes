---
name: recipe-to-home-assistant
description: Add a recipe to the Recipe Book integration in the user's Home Assistant from a photo (a cookbook page, recipe card, handwritten note or screenshot); also list, read, correct, set the status of and delete stored recipes. Use whenever the user shares a photo of a recipe or asks to save, find, change or delete a recipe, even without mentioning Home Assistant.
---

# Recipe photo → Home Assistant

The user takes a photo of a recipe. You read it, turn it into a recipe file, and add it to the Recipe Book integration in their Home Assistant (https://github.com/davidmorton0/home-assistant-recipes). Stored recipes can also be listed, read, corrected, have their status set, and deleted (step 4).

The script `scripts/recipes_to_ha.py` does every call. It reads the Home Assistant address and a long-lived access token from `config.json` in the skill folder.

## Step 1: Read the photo

Copy the recipe as written. Do not invent anything that is not on the page.

- **name:** the recipe's title.
- **category:** a short group such as Soup, Curry, Pasta, Baking, Breakfast. First run `list` and reuse an existing category that fits, spelt the same way, so the card's category picker does not get near-duplicates. If none fits, use a new one.
- **serves:** the number of servings on the page, as a whole number. "Serves 4–6" → 4. Leave it out if the page gives none (the integration then stores 2).
- **ingredients:** one entry per ingredient, with its amount, as on the page ("400 g chopped tomatoes"). Keep group headings as their own entry ending in a colon ("For the sauce:").
- **steps:** one entry per step, in order. Do not number them; the card shows them in order. Split a long paragraph only where the page itself starts a new step.
- **status:** leave it out (Untested) unless the user says they have made it.

Text cut off, blurred or hidden by a thumb: if it changes an amount or a step, ask one short question about that part. Otherwise go on.

If the photo shows several recipes, ask which ones to add.

If the photo spans several pages, the user may send more photos: wait for them before adding.

## Step 2: Check it is not already stored

Run `list --search "<a word from the name>"`. If a recipe with the same name is there, ask whether to add it as a new recipe or replace the stored one (`update`, step 4).

## Step 3: Add it

Write the recipe file and run the script:

```json
{
  "name": "Tomato soup",
  "category": "Soup",
  "serves": 4,
  "ingredients": ["1 onion", "400 g chopped tomatoes", "500 ml vegetable stock"],
  "steps": ["Fry the onion for 5 minutes.", "Add the tomatoes and stock and simmer for 20 minutes.", "Blend."]
}
```

```bash
python /path/to/skill/scripts/recipes_to_ha.py add recipe.json
```

- `name` and `category` up to 100 characters; `serves` a whole number 0–100; `status` one of Untested, Attempted, Approved.
- `ingredients` and `steps` are lists of strings and must not be empty.
- `--dry-run` checks the file and prints what would be sent, without sending.
- The script prints `added '<name>' <uuid>`.

A recipe is added in one call: if it is refused, nothing is stored.

### If sending fails

Report what the script printed, plainly. By cause:

- **"BLOCKED BY SANDBOX NETWORK":** the Home Assistant domain is not in the allowed domains list for code execution in Claude's settings.
- **401:** the token in `config.json` is wrong or revoked. Repeated failures can get the address banned by Home Assistant, so don't retry; ask the user to check the token.
- **400:** the reply says what was refused; fix the recipe file and send again (nothing was stored).
- **"could not connect":** nothing was stored; check the address and that Home Assistant is up.
- **"did not reply in time":** the recipe may have been stored. Run `list --search` with its name before sending again, so it is not stored twice.
- **config.json placeholders:** ask the user for their Home Assistant address and a long-lived access token.

Still show the user the recipe you read even if sending fails, so the work is not lost.

## Step 4: Listing, reading, correcting, status and deleting

```bash
python scripts/recipes_to_ha.py list                        # every recipe, one per line, ending in its uuid
python scripts/recipes_to_ha.py list --category Soup
python scripts/recipes_to_ha.py list --search lentil        # text in the name or an ingredient
python scripts/recipes_to_ha.py get <uuid>                  # one recipe, as a recipe file
python scripts/recipes_to_ha.py update <uuid> fixed.json    # replace every field
python scripts/recipes_to_ha.py status <uuid> Approved
python scripts/recipes_to_ha.py delete <uuid>
```

- `list` and `get` answer questions such as "what soups do I have" or "what's in the lentil curry".
- To correct a recipe: `get` it, save the printed recipe file, change only what the user asked for, then `update`. `update` replaces every field, so a field left out of the file is reset to its default.
- `status` sets Untested, Attempted or Approved and changes nothing else.
- `delete` removes the recipe's file. Ask the user before deleting, unless they named the recipe to delete.

## Step 5: Show the user what was stored

After a successful add or update, reply in exactly this format, kept short because the user is usually on a phone:

```
Added Tomato soup (Soup, serves 4): 3 ingredients, 3 steps
```

- Use "Updated" for an update.
- Then one line naming anything you could not read and how you filled it, if any (`Unclear: stock amount, written as 500 ml`). Otherwise nothing more.
