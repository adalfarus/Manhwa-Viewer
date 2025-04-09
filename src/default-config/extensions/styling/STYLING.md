### What Are `.th` and `.st` Files, and How Do They Work?

#### `.th` Files:

`.th` files are theme files where the filename is important. The first word of the filename indicates the creator, followed by the theme name. For example:

`adalfarus_cool_theme.th`  
This is a theme called "Cool Theme" by the creator "adalfarus." Naming themes this way avoids conflicts when linking to `.st` files later.

**Key Parts of a `.th` File:**

1. **Inheriting or Extending Styles**  
   - **Extending:** Adds new properties without overwriting existing ones. Themes are applied in reverse order: your theme first, then the base.  
     Example:  
     ```  
     extending adalfarus::base;  
     ```  
   - **Inheriting:** Allows overwriting properties from a base theme. The base theme is applied first, then your changes.  
     Example:  
     ```  
     inheriting adalfarus::base;  
     ```

2. **Base Attributes**  
   The first line specifies base app styles, compatibility, and precautions in this format:  
   `base_app_style/compatible_styling/style_precautions`  
   - **Base App Styles:** Built-in styles from Qt6 (e.g., Default, Fusion, Windows 11).  
   - **Compatible Styling:** Options include `light`, `dark`, `*` (both light/dark), or `os` (OS-dependent theming).  
   - **Style Precautions:** `new_st` (introduces new colors) or `reuse_st` (reuses base styles).

3. **QSS Styling**  
   Actual styles are defined in QSS format with placeholders for colors. Example:  
   ```css
   QPushButton {
       background-color: $button_color;
       color: $button_text_color;
   }
   ```

4. **Placeholders (`ph:`)**  
   Define placeholders for colors.  
   - `~=`: Changeable.  
   - `==`: Fixed value.  
   Example:  
   ```
   ph:
   dark_color~=#111111;
   button_color==#007bff;
   ```

**Sample `.th` File:**  
```  
inheriting adalfarus::base;  
Fusion/os/color  

QPushButton { background-color: $button_color; }  

ph:  
button_color~=#007bff;  
```

---

#### `.st` Files:

`.st` files define style-specific settings and link to compatible themes.

1. **Theme Compatibility (`for` Command)**  
   Specifies which themes can use the style. Use `*` for wildcards. Example:  
   ```
   for adalfarus::{thick::*, thin::*};
   ```

2. **Placeholders**  
   Define color attributes for `QPalette` and Qt global colors. Example:  
   ```  
   QPalette[
       background: rgba(10, 22, 211, 0.1);
   ];
   white: #ffffff;
   ```

3. **Transparency**  
   - Add transparency manually or dynamically by appending `T` to color definitions. Example:  
     ```
     background_secondaryT: rgba(255, 222, 111, 200);
     ```

By combining `.th` and `.st` files, you can create modular and reusable themes with dynamic customization options.