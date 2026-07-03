with open('app/templates/category/view.html', 'r') as f:
    content = f.read()

import re

# We need to insert the buttons and </form> right after </table>
# But wait, we need to make sure we don't insert it multiple times.
# Let's find </table>\n            </div>
# and replace it.

pattern = re.compile(r'(</form>\s*{%\s*endif\s*%}\s*)?</div>\s*</div>\s*{%\s*endfor\s*%}')

# First, clean up any hanging </div> </div> {% endfor %}
# Wait, let's just do a simple replacement of the whole block.
# We know the block starts with </table> and ends with {% endfor %}

target = """                </table>
            </div>

            
        </div>
        {% endfor %}"""

replacement = """                </table>
                {% if current_user and current_user.role in ['admin', 'superadmin'] and category.status == 'in_progress' %}
                <div style="display: flex; gap: 8px; justify-content: flex-end; margin-top: 1rem; margin-bottom: 1rem;">
                    <button type="submit" class="btn btn-primary" title="Save Entries" style="padding: 0.5rem; display: flex; align-items: center; justify-content: center; border-radius: 4px;">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>
                    </button>
                    <button type="reset" class="btn" title="Undo Entries" style="padding: 0.5rem; display: flex; align-items: center; justify-content: center; border-radius: 4px; background: rgba(255,255,255,0.1);">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 7v6h6"></path><path d="M21 17a9 9 0 0 0-9-9 9 9 0 0 0-6 2.3L3 13"></path></svg>
                    </button>
                </div>
                </form>
                {% endif %}
            </div>
        </div>
        {% endfor %}"""

if target in content:
    content = content.replace(target, replacement)
else:
    print("Could not find exact target, trying regex")
    # regex fallback
    target_pattern = re.compile(r'</table>\s*</div>\s*</div>\s*{%\s*endfor\s*%}')
    content = target_pattern.sub(replacement.replace('                </table>', '</table>'), content)

with open('app/templates/category/view.html', 'w') as f:
    f.write(content)
