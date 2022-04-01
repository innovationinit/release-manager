from django import forms

from releases.versioning import VersioningScheme


class MergeRequestForm(forms.Form):
    project_gitlab_id = forms.CharField()
    source_branch = forms.CharField()
    target_branch = forms.CharField()


class TagForm(forms.Form):
    project_gitlab_id = forms.CharField(widget=forms.HiddenInput())
    major = forms.IntegerField()
    minor = forms.IntegerField()
    patch = forms.IntegerField()
    fix = forms.IntegerField()

    def __init__(self, *args, versioning_scheme: VersioningScheme, **kwargs):
        super().__init__(*args, **kwargs)
        for field, segment in [
            ('major', versioning_scheme.MAJOR_SEGMENT),
            ('minor', versioning_scheme.MINOR_SEGMENT),
            ('patch', versioning_scheme.PATCH_SEGMENT),
            ('fix', versioning_scheme.FIX_SEGMENT),
        ]:
            self.fields[field].label = segment.label
            self.fields[field].help_text = segment.help_text
            self.fields[field].required = segment.required
            self.fields[field].initial = segment.initial
            self.fields[field].min_value = segment.min_value


class PostDeploymentHookForm(forms.Form):
    project_gitlab_id = forms.CharField()
