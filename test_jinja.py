from jinja2 import Template

t = Template("score: '{{ score1 or '' }}'")
print(t.render(score1=None))
