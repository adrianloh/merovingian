import nk

nuke.addAfterRender(nk.afterRender)
nuke.addOnScriptLoad(nk.dynamicFavorites)
nuke.addOnScriptLoad(nk.initRelativePaths)
nuke.addOnUserCreate(nk.customizeNodeOnUserCreate)