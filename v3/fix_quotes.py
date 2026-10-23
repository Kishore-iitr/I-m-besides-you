import re

with open('generate_app.py', 'r', encoding='utf-8') as f:
    c = f.read()

# Replace the unescaped quote occurrences
old_render = """      tbody.innerHTML = activeExtractedRules.map(function(r, idx) {
        const isHold = (r.action_on_match === 'Hold' || r.action_on_match === 'Rejected');
        return '<tr>' +
          '<td style="text-align: center; color: #64748b;">' + (idx + 1) + '</td>' +
          '<td><input type="text" value="' + (r.rule_id || '') + '" onchange="updateRuleCell(' + idx + ', \'rule_id\', this.value)" style="width: 75px; font-weight: 600;"></td>' +
          '<td><input type="text" value="' + (r.match_value || r.name || '') + '" onchange="updateRuleCell(' + idx + ', \'match_value\', this.value)"></td>' +
          '<td><input type="text" value="' + (r.condition || '') + '" onchange="updateRuleCell(' + idx + ', \'condition\', this.value)"></td>' +
          '<td>' +
            '<select onchange="updateRuleCell(' + idx + ', \'action_on_match\', this.value)" style="font-weight: 700; color: ' + (isHold ? '#b91c1c' : '#15803d') + ';">' +
              '<option value="Approved" ' + (r.action_on_match === 'Approved' ? 'selected' : '') + '>Approved</option>' +
              '<option value="Confirmed" ' + (r.action_on_match === 'Confirmed' ? 'selected' : '') + '>Confirmed</option>' +
              '<option value="Hold" ' + (r.action_on_match === 'Hold' ? 'selected' : '') + '>Hold</option>' +
              '<option value="Rejected" ' + (r.action_on_match === 'Rejected' ? 'selected' : '') + '>Rejected</option>' +
            '</select>' +
          '</td>' +
          '<td><input type="text" value="' + (r.description || '') + '" onchange="updateRuleCell(' + idx + ', \'description\', this.value)"></td>' +
          '<td style="text-align: center;">' +
            '<button class="btn-secondary" style="padding: 1px 4px; font-size: 10px; color: #b91c1c;" onclick="deleteExtractedRule(' + idx + ')">✕</button>' +
          '</td>' +
        '</tr>';
      }).join('');"""

new_render = """      tbody.innerHTML = activeExtractedRules.map(function(r, idx) {
        const isHold = (r.action_on_match === 'Hold' || r.action_on_match === 'Rejected');
        return '<tr>' +
          '<td style="text-align: center; color: #64748b;">' + (idx + 1) + '</td>' +
          '<td><input type="text" value="' + (r.rule_id || '') + '" onchange="updateRuleCell(' + idx + ', &quot;rule_id&quot;, this.value)" style="width: 75px; font-weight: 600;"></td>' +
          '<td><input type="text" value="' + (r.match_value || r.name || '') + '" onchange="updateRuleCell(' + idx + ', &quot;match_value&quot;, this.value)"></td>' +
          '<td><input type="text" value="' + (r.condition || '') + '" onchange="updateRuleCell(' + idx + ', &quot;condition&quot;, this.value)"></td>' +
          '<td>' +
            '<select onchange="updateRuleCell(' + idx + ', &quot;action_on_match&quot;, this.value)" style="font-weight: 700; color: ' + (isHold ? '#b91c1c' : '#15803d') + ';">' +
              '<option value="Approved" ' + (r.action_on_match === 'Approved' ? 'selected' : '') + '>Approved</option>' +
              '<option value="Confirmed" ' + (r.action_on_match === 'Confirmed' ? 'selected' : '') + '>Confirmed</option>' +
              '<option value="Hold" ' + (r.action_on_match === 'Hold' ? 'selected' : '') + '>Hold</option>' +
              '<option value="Rejected" ' + (r.action_on_match === 'Rejected' ? 'selected' : '') + '>Rejected</option>' +
            '</select>' +
          '</td>' +
          '<td><input type="text" value="' + (r.description || '') + '" onchange="updateRuleCell(' + idx + ', &quot;description&quot;, this.value)"></td>' +
          '<td style="text-align: center;">' +
            '<button class="btn-secondary" style="padding: 1px 4px; font-size: 10px; color: #b91c1c;" onclick="deleteExtractedRule(' + idx + ')">✕</button>' +
          '</td>' +
        '</tr>';
      }).join('');"""

c_norm = c.replace('\r\n', '\n')
old_norm = old_render.replace('\r\n', '\n')
new_norm = new_render.replace('\r\n', '\n')

if old_norm in c_norm:
    c_norm = c_norm.replace(old_norm, new_norm)
    with open('generate_app.py', 'w', encoding='utf-8') as f:
        f.write(c_norm)
    print("Successfully updated generate_app.py with &quot;!")
else:
    print("Target block not found directly, looking for close match...")
    # Let's inspect where renderExtractedRulesTable is
    idx = c_norm.find('function renderExtractedRulesTable()')
    print("renderExtractedRulesTable at index:", idx)
    snippet = c_norm[idx:idx+1200]
    print("Snippet:")
    print(snippet)
